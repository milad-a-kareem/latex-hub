from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from app.routers import compile as compile_router


@pytest.fixture
def patched_compile(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Replace tectonic + storage with stubs so we don't shell out or hit GCS.

    The dict captures the arguments compile_latex was called with so the test
    can verify entry/assets propagation.
    """
    captured: dict[str, Any] = {}

    async def fake_compile(
        workdir: Path,
        files: dict[str, str],
        entry: str = "main.tex",
        assets: dict[str, bytes] | None = None,
    ) -> bytes:
        captured["entry"] = entry
        captured["files"] = files
        captured["assets"] = assets or {}
        return b"%PDF-fake"

    def fake_upload(project_id: str, pdf: bytes) -> str:
        captured["uploaded_size"] = len(pdf)
        return f"https://example.com/{project_id}.pdf"

    def fake_download(project_id: str, path: str) -> bytes:
        return b"BINARYDATA-" + path.encode()

    monkeypatch.setattr(compile_router, "compile_latex", fake_compile)
    monkeypatch.setattr(compile_router, "upload_pdf", fake_upload)
    monkeypatch.setattr(compile_router, "download_asset_bytes", fake_download)
    return captured


def _create(client: Any, name: str = "demo") -> str:
    return str(client.post("/api/projects", json={"name": name}).json()["id"])


def test_compile_uses_entry(client: Any, patched_compile: dict[str, Any]) -> None:
    pid = _create(client)
    client.post(f"/api/projects/{pid}/files", json={"path": "paper.tex", "content": "X"})
    client.put(f"/api/projects/{pid}/entry", json={"entry": "paper.tex"})

    r = client.post(f"/api/projects/{pid}/compile")
    assert r.status_code == 200
    assert r.json()["pdfUrl"].endswith(f"{pid}.pdf")
    assert patched_compile["entry"] == "paper.tex"


def test_compile_stages_assets(
    client: Any,
    fake_db: Any,
    patched_compile: dict[str, Any],
) -> None:
    pid = _create(client)

    # Inject an asset directly into the fake Firestore so we don't need a
    # real Storage upload in this unit test.
    fake_db.get_store("projects")[pid]["assets"] = {
        "img/figure.png": {"size": 11, "contentType": "image/png", "updatedAt": "now"}
    }

    r = client.post(f"/api/projects/{pid}/compile")
    assert r.status_code == 200
    assert "img/figure.png" in patched_compile["assets"]
    assert patched_compile["assets"]["img/figure.png"].startswith(b"BINARYDATA-")


def test_compile_400_when_entry_missing(client: Any, fake_db: Any) -> None:
    pid = _create(client)
    # Remove main.tex from the underlying store
    fake_db.get_store("projects")[pid]["files"] = {}
    r = client.post(f"/api/projects/{pid}/compile")
    assert r.status_code == 400
