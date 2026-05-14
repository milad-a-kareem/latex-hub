from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from ..auth import CurrentUserDep
from ..config import get_settings
from ..firebase import db
from ..services.storage import upload_pdf
from ..services.tectonic import CompileError, compile_latex

router = APIRouter(prefix="/api/projects", tags=["compile"])


class CompileOut(BaseModel):
    pdfUrl: str  # noqa: N815
    log: str


@router.post("/{project_id}/compile", response_model=CompileOut)
async def compile_project(project_id: str, user: CurrentUserDep) -> CompileOut:
    snap = db().collection("projects").document(project_id).get()
    if not snap.exists:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    data = snap.to_dict() or {}
    if data.get("ownerUid") != user.uid:
        raise HTTPException(status.HTTP_403_FORBIDDEN)

    files: dict[str, str] = dict(data.get("files") or {})
    if "main.tex" not in files:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "main.tex is required")

    workdir = Path(get_settings().compile_workdir)
    try:
        pdf = await compile_latex(workdir, files)
    except CompileError as exc:
        return CompileOut(pdfUrl="", log=exc.log)

    url = upload_pdf(project_id, pdf)
    return CompileOut(pdfUrl=url, log="ok")
