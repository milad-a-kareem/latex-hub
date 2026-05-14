from datetime import UTC, datetime
from typing import Any

from google.cloud.firestore import SERVER_TIMESTAMP

from ..firebase import db

DEFAULT_MAIN_TEX = r"""\documentclass{article}
\begin{document}
Hello, \textbf{latex-hub}!
\end{document}
"""


def _coll() -> Any:
    return db().collection("projects")


def list_projects(uid: str) -> list[dict[str, Any]]:
    query = _coll().where("ownerUid", "==", uid).order_by("updatedAt", direction="DESCENDING")
    return [_serialize(doc.id, doc.to_dict()) for doc in query.stream()]


def create_project(uid: str, name: str) -> dict[str, Any]:
    doc_ref = _coll().document()
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "name": name,
        "ownerUid": uid,
        "files": {"main.tex": DEFAULT_MAIN_TEX},
        "createdAt": SERVER_TIMESTAMP,
        "updatedAt": SERVER_TIMESTAMP,
    }
    doc_ref.set(payload)
    return _serialize(doc_ref.id, {**payload, "createdAt": now, "updatedAt": now})


def get_project(uid: str, project_id: str) -> dict[str, Any] | None:
    snap = _coll().document(project_id).get()
    if not snap.exists:
        return None
    data: dict[str, Any] = snap.to_dict() or {}
    if data.get("ownerUid") != uid:
        return None
    return _serialize(snap.id, data)


def update_file(uid: str, project_id: str, path: str, content: str) -> None:
    doc_ref = _coll().document(project_id)
    snap = doc_ref.get()
    if not snap.exists or (snap.to_dict() or {}).get("ownerUid") != uid:
        raise PermissionError("not found or forbidden")
    doc_ref.update({f"files.{path}": content, "updatedAt": SERVER_TIMESTAMP})


def _serialize(doc_id: str, data: dict[str, Any]) -> dict[str, Any]:
    updated = data.get("updatedAt")
    return {
        "id": doc_id,
        "name": data.get("name", ""),
        "updatedAt": updated.isoformat() if isinstance(updated, datetime) else "",
    }
