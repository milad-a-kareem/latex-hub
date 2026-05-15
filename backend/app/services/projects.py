from datetime import UTC, datetime
from typing import Any

from google.cloud.firestore import DELETE_FIELD, SERVER_TIMESTAMP

from ..firebase import db

DEFAULT_MAIN_TEX = r"""\documentclass{article}
\begin{document}
Hello, \textbf{latex-hub}!
\end{document}
"""

DEFAULT_ENTRY = "main.tex"

TEXT_EXTENSIONS = frozenset({".tex", ".bib", ".cls", ".sty", ".txt", ".md", ".bst"})

MAX_PATH_LEN = 256


class PathError(ValueError):
    """Raised when a file path is unsafe or invalid."""


def safe_path(path: str) -> str:
    p = path.strip()
    if not p:
        raise PathError("empty path")
    if p.startswith("/") or "\\" in p or ".." in p.split("/"):
        raise PathError("invalid path")
    if len(p) > MAX_PATH_LEN:
        raise PathError("path too long")
    return p


def is_text_path(path: str) -> bool:
    lower = path.lower()
    return any(lower.endswith(ext) for ext in TEXT_EXTENSIONS)


def _coll() -> Any:
    return db().collection("projects")


def require_owned(uid: str, project_id: str) -> dict[str, Any]:
    snap = _coll().document(project_id).get()
    if not snap.exists:
        raise PermissionError("not found")
    data: dict[str, Any] = snap.to_dict() or {}
    if data.get("ownerUid") != uid:
        raise PermissionError("forbidden")
    return data


def list_projects(uid: str) -> list[dict[str, Any]]:
    query = _coll().where("ownerUid", "==", uid).order_by("updatedAt", direction="DESCENDING")
    return [_summary(doc.id, doc.to_dict()) for doc in query.stream()]


def create_project(uid: str, name: str) -> dict[str, Any]:
    doc_ref = _coll().document()
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "name": name,
        "ownerUid": uid,
        "files": {DEFAULT_ENTRY: DEFAULT_MAIN_TEX},
        "assets": {},
        "entry": DEFAULT_ENTRY,
        "createdAt": SERVER_TIMESTAMP,
        "updatedAt": SERVER_TIMESTAMP,
    }
    doc_ref.set(payload)
    return _summary(doc_ref.id, {**payload, "createdAt": now, "updatedAt": now})


def get_project(uid: str, project_id: str) -> dict[str, Any] | None:
    try:
        data = require_owned(uid, project_id)
    except PermissionError:
        return None
    return _summary(project_id, data)


def get_project_full(uid: str, project_id: str) -> dict[str, Any] | None:
    try:
        data = require_owned(uid, project_id)
    except PermissionError:
        return None
    files: dict[str, str] = dict(data.get("files") or {})
    assets_raw: dict[str, Any] = dict(data.get("assets") or {})
    assets = [
        {
            "path": path,
            "size": int(meta.get("size", 0)),
            "contentType": str(meta.get("contentType", "application/octet-stream")),
        }
        for path, meta in assets_raw.items()
    ]
    return {
        "id": project_id,
        "name": data.get("name", ""),
        "entry": data.get("entry") or DEFAULT_ENTRY,
        "files": files,
        "assets": assets,
    }


def rename_project(uid: str, project_id: str, name: str) -> dict[str, Any]:
    require_owned(uid, project_id)
    doc_ref = _coll().document(project_id)
    doc_ref.update({"name": name, "updatedAt": SERVER_TIMESTAMP})
    snap = doc_ref.get()
    return _summary(project_id, snap.to_dict() or {})


def delete_project(uid: str, project_id: str) -> None:
    require_owned(uid, project_id)
    _coll().document(project_id).delete()


def read_file(uid: str, project_id: str, path: str) -> str | None:
    safe = safe_path(path)
    try:
        data = require_owned(uid, project_id)
    except PermissionError:
        return None
    files: dict[str, str] = data.get("files") or {}
    return files.get(safe)


def update_file(uid: str, project_id: str, path: str, content: str) -> None:
    safe = safe_path(path)
    require_owned(uid, project_id)
    doc_ref = _coll().document(project_id)
    doc_ref.update({f"files.{safe}": content, "updatedAt": SERVER_TIMESTAMP})


def create_file(uid: str, project_id: str, path: str, content: str = "") -> None:
    safe = safe_path(path)
    if not is_text_path(safe):
        raise PathError("not a text file extension")
    data = require_owned(uid, project_id)
    files: dict[str, Any] = data.get("files") or {}
    if safe in files:
        raise PathError("file exists")
    doc_ref = _coll().document(project_id)
    doc_ref.update({f"files.{safe}": content, "updatedAt": SERVER_TIMESTAMP})


def delete_file(uid: str, project_id: str, path: str) -> None:

    safe = safe_path(path)
    data = require_owned(uid, project_id)
    files: dict[str, Any] = data.get("files") or {}
    if safe not in files:
        raise PathError("file does not exist")
    if (data.get("entry") or DEFAULT_ENTRY) == safe:
        raise PathError("cannot delete the compile entry file")
    doc_ref = _coll().document(project_id)
    doc_ref.update({f"files.{safe}": DELETE_FIELD, "updatedAt": SERVER_TIMESTAMP})


def rename_file(uid: str, project_id: str, old_path: str, new_path: str) -> None:

    src = safe_path(old_path)
    dst = safe_path(new_path)
    if src == dst:
        return
    if not is_text_path(dst):
        raise PathError("destination is not a text file extension")
    data = require_owned(uid, project_id)
    files: dict[str, Any] = data.get("files") or {}
    if src not in files:
        raise PathError("source file does not exist")
    if dst in files:
        raise PathError("destination file exists")
    update: dict[str, Any] = {
        f"files.{src}": DELETE_FIELD,
        f"files.{dst}": files[src],
        "updatedAt": SERVER_TIMESTAMP,
    }
    if (data.get("entry") or DEFAULT_ENTRY) == src:
        update["entry"] = dst
    _coll().document(project_id).update(update)


def set_entry(uid: str, project_id: str, entry: str) -> None:
    safe = safe_path(entry)
    if not safe.lower().endswith(".tex"):
        raise PathError("entry must be a .tex file")
    data = require_owned(uid, project_id)
    files: dict[str, Any] = data.get("files") or {}
    if safe not in files:
        raise PathError("entry file does not exist")
    _coll().document(project_id).update({"entry": safe, "updatedAt": SERVER_TIMESTAMP})


def record_asset(
    uid: str,
    project_id: str,
    path: str,
    size: int,
    content_type: str,
) -> None:
    safe = safe_path(path)
    if is_text_path(safe):
        raise PathError("text files belong in files, not assets")
    require_owned(uid, project_id)
    now_iso = datetime.now(UTC).isoformat()
    _coll().document(project_id).update(
        {
            f"assets.{safe}": {
                "size": size,
                "contentType": content_type,
                "updatedAt": now_iso,
            },
            "updatedAt": SERVER_TIMESTAMP,
        }
    )


def remove_asset(uid: str, project_id: str, path: str) -> None:

    safe = safe_path(path)
    data = require_owned(uid, project_id)
    assets: dict[str, Any] = data.get("assets") or {}
    if safe not in assets:
        raise PathError("asset does not exist")
    _coll().document(project_id).update(
        {f"assets.{safe}": DELETE_FIELD, "updatedAt": SERVER_TIMESTAMP}
    )


def list_asset_paths(uid: str, project_id: str) -> list[str]:
    try:
        data = require_owned(uid, project_id)
    except PermissionError:
        return []
    return list((data.get("assets") or {}).keys())


def _summary(doc_id: str, data: dict[str, Any]) -> dict[str, Any]:
    updated = data.get("updatedAt")
    return {
        "id": doc_id,
        "name": data.get("name", ""),
        "updatedAt": updated.isoformat() if isinstance(updated, datetime) else "",
    }
