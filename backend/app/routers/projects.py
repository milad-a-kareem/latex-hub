import contextlib

from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from ..auth import CurrentUserDep
from ..services import projects as svc
from ..services import storage as storage_svc

router = APIRouter(prefix="/api/projects", tags=["projects"])

MAX_ASSET_BYTES = 25 * 1024 * 1024  # 25 MiB


class CreateProjectIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class RenameProjectIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class ProjectOut(BaseModel):
    id: str
    name: str
    updatedAt: str


class AssetOut(BaseModel):
    path: str
    size: int
    contentType: str


class ProjectFullOut(BaseModel):
    id: str
    name: str
    entry: str
    files: dict[str, str]
    assets: list[AssetOut]


class FileUpdateIn(BaseModel):
    content: str


class CreateFileIn(BaseModel):
    path: str = Field(min_length=1, max_length=256)
    content: str = ""


class RenameFileIn(BaseModel):
    newPath: str = Field(min_length=1, max_length=256)


class SetEntryIn(BaseModel):
    entry: str = Field(min_length=1, max_length=256)


def _path_err(exc: svc.PathError) -> HTTPException:
    return HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))


@router.get("", response_model=list[ProjectOut])
async def list_projects(user: CurrentUserDep) -> list[ProjectOut]:
    return [ProjectOut(**p) for p in svc.list_projects(user.uid)]


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
async def create_project(body: CreateProjectIn, user: CurrentUserDep) -> ProjectOut:
    return ProjectOut(**svc.create_project(user.uid, body.name))


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(project_id: str, user: CurrentUserDep) -> ProjectOut:
    p = svc.get_project(user.uid, project_id)
    if not p:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    return ProjectOut(**p)


@router.get("/{project_id}/full", response_model=ProjectFullOut)
async def get_project_full(project_id: str, user: CurrentUserDep) -> ProjectFullOut:
    p = svc.get_project_full(user.uid, project_id)
    if not p:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    return ProjectFullOut(**p)


@router.patch("/{project_id}", response_model=ProjectOut)
async def rename_project(
    project_id: str,
    body: RenameProjectIn,
    user: CurrentUserDep,
) -> ProjectOut:
    try:
        return ProjectOut(**svc.rename_project(user.uid, project_id, body.name))
    except PermissionError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND) from exc


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(project_id: str, user: CurrentUserDep) -> None:
    try:
        svc.delete_project(user.uid, project_id)
    except PermissionError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND) from exc
    # Best-effort GCS cleanup; ignore failures so a partial cleanup doesn't
    # block the Firestore delete from being acknowledged.
    with contextlib.suppress(Exception):
        storage_svc.delete_project_prefix(project_id)


@router.put("/{project_id}/files/{path:path}", status_code=status.HTTP_204_NO_CONTENT)
async def update_file(
    project_id: str,
    path: str,
    body: FileUpdateIn,
    user: CurrentUserDep,
) -> None:
    try:
        svc.update_file(user.uid, project_id, path, body.content)
    except PermissionError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND) from exc
    except svc.PathError as exc:
        raise _path_err(exc) from exc


@router.post("/{project_id}/files", status_code=status.HTTP_201_CREATED)
async def create_file(
    project_id: str,
    body: CreateFileIn,
    user: CurrentUserDep,
) -> Response:
    try:
        svc.create_file(user.uid, project_id, body.path, body.content)
    except PermissionError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND) from exc
    except svc.PathError as exc:
        raise _path_err(exc) from exc
    return Response(status_code=status.HTTP_201_CREATED)


@router.delete("/{project_id}/files/{path:path}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file(project_id: str, path: str, user: CurrentUserDep) -> None:
    try:
        svc.delete_file(user.uid, project_id, path)
    except PermissionError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND) from exc
    except svc.PathError as exc:
        raise _path_err(exc) from exc


@router.post(
    "/{project_id}/files/{path:path}/rename",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def rename_file(
    project_id: str,
    path: str,
    body: RenameFileIn,
    user: CurrentUserDep,
) -> None:
    try:
        svc.rename_file(user.uid, project_id, path, body.newPath)
    except PermissionError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND) from exc
    except svc.PathError as exc:
        raise _path_err(exc) from exc


@router.put("/{project_id}/entry", status_code=status.HTTP_204_NO_CONTENT)
async def set_entry(
    project_id: str,
    body: SetEntryIn,
    user: CurrentUserDep,
) -> None:
    try:
        svc.set_entry(user.uid, project_id, body.entry)
    except PermissionError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND) from exc
    except svc.PathError as exc:
        raise _path_err(exc) from exc


@router.post("/{project_id}/assets/{path:path}", status_code=status.HTTP_201_CREATED)
async def upload_asset(
    project_id: str,
    path: str,
    request: Request,
    user: CurrentUserDep,
) -> Response:
    data = await request.body()
    if len(data) == 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "empty body")
    if len(data) > MAX_ASSET_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "asset too large")
    content_type = request.headers.get("content-type") or "application/octet-stream"
    try:
        # Ownership check happens before the Storage write so we don't
        # upload bytes we'll never be able to reference.
        svc.require_owned(user.uid, project_id)
        safe = svc.safe_path(path)
        if svc.is_text_path(safe):
            raise svc.PathError("use the files endpoint for text files")
    except PermissionError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND) from exc
    except svc.PathError as exc:
        raise _path_err(exc) from exc

    try:
        storage_svc.upload_asset(project_id, safe, data, content_type)
        svc.record_asset(user.uid, project_id, safe, len(data), content_type)
    except svc.PathError as exc:
        raise _path_err(exc) from exc
    return Response(status_code=status.HTTP_201_CREATED)


@router.get("/{project_id}/assets/{path:path}")
async def get_asset(project_id: str, path: str, user: CurrentUserDep) -> RedirectResponse:
    try:
        svc.require_owned(user.uid, project_id)
        safe = svc.safe_path(path)
    except PermissionError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND) from exc
    except svc.PathError as exc:
        raise _path_err(exc) from exc
    url = storage_svc.signed_asset_url(project_id, safe)
    return RedirectResponse(url, status_code=status.HTTP_302_FOUND)


@router.delete("/{project_id}/assets/{path:path}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_asset(project_id: str, path: str, user: CurrentUserDep) -> None:
    try:
        svc.remove_asset(user.uid, project_id, path)
    except PermissionError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND) from exc
    except svc.PathError as exc:
        raise _path_err(exc) from exc
    with contextlib.suppress(Exception):
        storage_svc.delete_asset(project_id, path)
