"""Yjs room persistence: seed from Firestore and debounce-write snapshots back.

A ``RoomSnapshotter`` is held module-global by ``collab.py``. It keeps a
background task per room while at least one WebSocket client is connected.
On each tick (every ``DEBOUNCE_SECONDS``) it diffs the current Y.Text
content against the last persisted value and writes it to Firestore via
``projects.update_file``. When the last client disconnects the task is
cancelled and a final flush is performed.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from logging import getLogger
from typing import Any

from pycrdt import Doc, Text

log = getLogger(__name__)

DEBOUNCE_SECONDS = 2.0

WriteFn = Callable[[str], Awaitable[None]]


class RoomSnapshotter:
    def __init__(self) -> None:
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._last: dict[str, str] = {}
        self._refcount: dict[str, int] = {}

    def seed(self, name: str, ydoc: "Doc[Any]", initial: str) -> None:
        """Insert ``initial`` text into the room's ydoc if the doc is empty.

        Called once per room creation, before any client edits arrive.
        """
        text = ydoc.get("content", type=Text)
        if len(text) == 0 and initial:
            text += initial
        self._last[name] = initial

    def attach(self, name: str, ydoc: "Doc[Any]", write: WriteFn) -> None:
        """Start (or join) the snapshot task for ``name``.

        Each connecting client calls this; the first one spins up the
        background loop, subsequent ones just bump the refcount.
        """
        self._refcount[name] = self._refcount.get(name, 0) + 1
        if name in self._tasks:
            return
        self._tasks[name] = asyncio.create_task(self._loop(name, ydoc, write))

    async def detach(self, name: str, ydoc: "Doc[Any]", write: WriteFn) -> None:
        """Decrement the refcount; on zero, cancel the task and flush once more."""
        self._refcount[name] = max(0, self._refcount.get(name, 0) - 1)
        if self._refcount[name] > 0:
            return
        task = self._tasks.pop(name, None)
        if task is not None:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception:
                log.exception("snapshot task ended with error: %s", name)
        await self._flush(name, ydoc, write)
        self._last.pop(name, None)
        self._refcount.pop(name, None)

    async def _loop(self, name: str, ydoc: "Doc[Any]", write: WriteFn) -> None:
        while True:
            await asyncio.sleep(DEBOUNCE_SECONDS)
            await self._flush(name, ydoc, write)

    async def _flush(self, name: str, ydoc: "Doc[Any]", write: WriteFn) -> None:
        text = ydoc.get("content", type=Text)
        current = str(text)
        if current == self._last.get(name):
            return
        try:
            await write(current)
            self._last[name] = current
        except Exception:
            log.exception("snapshot write failed: %s", name)
