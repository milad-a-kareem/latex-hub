from __future__ import annotations

from typing import Any

import pytest


def _create(client: Any, name: str = "demo") -> str:
    res = client.post("/api/projects", json={"name": name})
    assert res.status_code == 201, res.text
    return str(res.json()["id"])


def test_list_create_get(client: Any) -> None:
    pid = _create(client, "first")
    res = client.get("/api/projects")
    assert res.status_code == 200
    assert any(p["id"] == pid for p in res.json())

    full = client.get(f"/api/projects/{pid}/full").json()
    assert full["entry"] == "main.tex"
    assert "main.tex" in full["files"]
    assert full["assets"] == []


def test_rename_and_delete(client: Any) -> None:
    pid = _create(client, "old")
    r = client.patch(f"/api/projects/{pid}", json={"name": "new"})
    assert r.status_code == 200
    assert r.json()["name"] == "new"

    r = client.delete(f"/api/projects/{pid}")
    assert r.status_code == 204
    assert client.get(f"/api/projects/{pid}").status_code == 404


def test_create_and_delete_file(client: Any) -> None:
    pid = _create(client)
    r = client.post(
        f"/api/projects/{pid}/files",
        json={"path": "intro.tex", "content": "\\section{Intro}"},
    )
    assert r.status_code == 201

    full = client.get(f"/api/projects/{pid}/full").json()
    assert full["files"]["intro.tex"] == "\\section{Intro}"

    r = client.delete(f"/api/projects/{pid}/files/intro.tex")
    assert r.status_code == 204
    full = client.get(f"/api/projects/{pid}/full").json()
    assert "intro.tex" not in full["files"]


def test_cannot_delete_entry(client: Any) -> None:
    pid = _create(client)
    r = client.delete(f"/api/projects/{pid}/files/main.tex")
    assert r.status_code == 400


def test_rename_file_updates_entry(client: Any) -> None:
    pid = _create(client)
    r = client.post(f"/api/projects/{pid}/files/main.tex/rename", json={"newPath": "paper.tex"})
    assert r.status_code == 204
    full = client.get(f"/api/projects/{pid}/full").json()
    assert "paper.tex" in full["files"]
    assert "main.tex" not in full["files"]
    assert full["entry"] == "paper.tex"


def test_set_entry_validates(client: Any) -> None:
    pid = _create(client)
    r = client.put(f"/api/projects/{pid}/entry", json={"entry": "missing.tex"})
    assert r.status_code == 400

    client.post(f"/api/projects/{pid}/files", json={"path": "other.tex"})
    r = client.put(f"/api/projects/{pid}/entry", json={"entry": "other.tex"})
    assert r.status_code == 204
    assert client.get(f"/api/projects/{pid}/full").json()["entry"] == "other.tex"


@pytest.mark.parametrize(
    "path",
    ["../escape.tex", "/abs/path.tex", "back\\slash.tex", "  ", ""],
)
def test_create_file_rejects_unsafe_paths(client: Any, path: str) -> None:
    pid = _create(client)
    r = client.post(f"/api/projects/{pid}/files", json={"path": path})
    assert r.status_code in (400, 422)


def test_create_file_rejects_non_text_extension(client: Any) -> None:
    pid = _create(client)
    r = client.post(f"/api/projects/{pid}/files", json={"path": "image.png"})
    assert r.status_code == 400


def test_get_full_404_for_unknown_project(client: Any) -> None:
    assert client.get("/api/projects/does-not-exist/full").status_code == 404
