from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from ..auth import CurrentUserDep
from ..services import projects as svc

router = APIRouter(prefix="/api/projects", tags=["projects"])


class CreateProjectIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class ProjectOut(BaseModel):
    id: str
    name: str
    updatedAt: str  # noqa: N815 — JSON-facing field


class FileUpdateIn(BaseModel):
    content: str


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
