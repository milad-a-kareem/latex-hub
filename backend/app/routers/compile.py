from pathlib import Path
from typing import Any, cast

from fastapi import APIRouter, HTTPException, status
from google.cloud.firestore import DocumentSnapshot
from pydantic import BaseModel

from ..auth import CurrentUserDep
from ..config import get_settings
from ..firebase import db
from ..services.storage import download_asset_bytes, upload_pdf
from ..services.tectonic import CompileError, compile_latex

router = APIRouter(prefix="/api/projects", tags=["compile"])

DEFAULT_ENTRY = "main.tex"


class CompileOut(BaseModel):
    pdfUrl: str
    log: str


@router.post("/{project_id}/compile", response_model=CompileOut)
async def compile_project(project_id: str, user: CurrentUserDep) -> CompileOut:
    snap = cast(DocumentSnapshot, db().collection("projects").document(project_id).get())
    if not snap.exists:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    data: dict[str, Any] = snap.to_dict() or {}
    if data.get("ownerUid") != user.uid:
        raise HTTPException(status.HTTP_403_FORBIDDEN)

    files: dict[str, str] = dict(data.get("files") or {})
    entry = str(data.get("entry") or DEFAULT_ENTRY)
    if entry not in files:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"entry file '{entry}' is missing from project files",
        )

    asset_meta: dict[str, Any] = dict(data.get("assets") or {})
    assets: dict[str, bytes] = {}
    for path in asset_meta:
        try:
            assets[path] = download_asset_bytes(project_id, path)
        except Exception:
            # missing asset shouldn't kill the compile; tectonic will surface
            # a "file not found" in its log if the .tex actually references it
            continue

    workdir = Path(get_settings().compile_workdir)
    try:
        pdf = await compile_latex(workdir, files, entry=entry, assets=assets)
    except CompileError as exc:
        return CompileOut(pdfUrl="", log=exc.log)

    url = upload_pdf(project_id, pdf)
    return CompileOut(pdfUrl=url, log="ok")
