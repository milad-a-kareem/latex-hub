from __future__ import annotations

import asyncio

import pytest
from app.ws import snapshot as snap_mod
from app.ws.snapshot import RoomSnapshotter
from pycrdt import Doc, Text


@pytest.mark.asyncio
async def test_seed_inserts_initial_content() -> None:
    snap = RoomSnapshotter()
    doc = Doc()
    snap.seed("room", doc, "hello world")
    assert str(doc.get("content", type=Text)) == "hello world"


@pytest.mark.asyncio
async def test_attach_writes_on_change(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(snap_mod, "DEBOUNCE_SECONDS", 0.05)
    snap = snap_mod.RoomSnapshotter()
    doc = Doc()
    snap.seed("room", doc, "initial")

    writes: list[str] = []

    async def write(s: str) -> None:
        writes.append(s)

    snap.attach("room", doc, write)
    # Mutate the text after the initial seed
    text = doc.get("content", type=Text)
    del text[:]
    text += "updated content"

    # Give the debounce task a tick or two to fire.
    await asyncio.sleep(0.2)
    await snap.detach("room", doc, write)

    assert "updated content" in writes


@pytest.mark.asyncio
async def test_detach_flushes_final(monkeypatch: pytest.MonkeyPatch) -> None:
    # Push the debounce window past the test's lifetime so the only flush
    # comes from detach().
    monkeypatch.setattr(snap_mod, "DEBOUNCE_SECONDS", 60.0)
    snap = snap_mod.RoomSnapshotter()
    doc = Doc()
    snap.seed("room", doc, "")

    writes: list[str] = []

    async def write(s: str) -> None:
        writes.append(s)

    snap.attach("room", doc, write)
    text = doc.get("content", type=Text)
    text += "last words"
    await snap.detach("room", doc, write)

    assert writes == ["last words"]


@pytest.mark.asyncio
async def test_refcount_keeps_task_alive() -> None:
    snap = RoomSnapshotter()
    doc = Doc()
    snap.seed("room", doc, "")

    async def write(_: str) -> None:
        pass

    snap.attach("room", doc, write)
    snap.attach("room", doc, write)
    assert "room" in snap._tasks  # type: ignore[attr-defined]

    await snap.detach("room", doc, write)
    # One detach; another client still connected — task should still be running.
    assert "room" in snap._tasks  # type: ignore[attr-defined]

    await snap.detach("room", doc, write)
    assert "room" not in snap._tasks  # type: ignore[attr-defined]
