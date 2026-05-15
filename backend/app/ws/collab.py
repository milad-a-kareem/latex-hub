"""Yjs collaboration WebSocket endpoint.

Each ``?room=<projectId:filePath>`` query maps to a ``YRoom`` held in memory
by ``pycrdt.websocket``'s :class:`WebsocketServer`. State is seeded from the
Firestore-persisted text on first connect and debounce-written back via the
``RoomSnapshotter`` so reconnecting users see the latest content even after
a Cloud Run scale event.
"""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status
from pycrdt.websocket import WebsocketServer
from pycrdt.websocket.yroom import YRoom

from ..firebase import verify_id_token
from ..services import projects as projects_svc
from .snapshot import RoomSnapshotter

router = APIRouter()
websocket_server = WebsocketServer(auto_clean_rooms=False)
snapshotter = RoomSnapshotter()


class _FastAPIChannel:
    """Adapter making a FastAPI ``WebSocket`` look like a pycrdt ``Channel``."""

    def __init__(self, ws: WebSocket, path: str) -> None:
        self._ws = ws
        self.path = path

    async def send(self, message: bytes) -> None:
        await self._ws.send_bytes(message)

    async def recv(self) -> bytes:
        try:
            return await self._ws.receive_bytes()
        except WebSocketDisconnect as exc:
            raise StopAsyncIteration from exc

    def __aiter__(self) -> _FastAPIChannel:
        return self

    async def __anext__(self) -> bytes:
        return await self.recv()


async def _verify_and_authorize(token: str, room: str) -> tuple[str, str, str] | None:
    """Verify the ID token and ownership of the project. Returns
    ``(uid, project_id, file_path)`` on success, or ``None`` on failure."""
    try:
        claims: dict[str, Any] = await asyncio.to_thread(verify_id_token, token)
    except Exception:
        return None
    uid = str(claims.get("uid") or "")
    if not uid:
        return None
    project_id, sep, file_path = room.partition(":")
    if not project_id or not sep or not file_path:
        return None
    try:
        await asyncio.to_thread(projects_svc.require_owned, uid, project_id)
    except PermissionError:
        return None
    try:
        projects_svc.safe_path(file_path)
    except projects_svc.PathError:
        return None
    return uid, project_id, file_path


@router.websocket("/ws/collab")
async def collab_ws(
    ws: WebSocket,
    token: str = Query(default=""),
    room: str = Query(...),
) -> None:
    auth = await _verify_and_authorize(token, room)
    if auth is None:
        await ws.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    uid, project_id, file_path = auth

    # If this is the first connection to the room, create + seed it before
    # WebsocketServer.serve() would otherwise create an empty one.
    if room not in websocket_server.rooms:
        yroom = YRoom(ready=True, log=websocket_server.log)
        initial = await asyncio.to_thread(projects_svc.read_file, uid, project_id, file_path)
        snapshotter.seed(room, yroom.ydoc, initial or "")
        websocket_server.rooms[room] = yroom

    yroom = websocket_server.rooms[room]

    async def write(text: str) -> None:
        await asyncio.to_thread(projects_svc.update_file, uid, project_id, file_path, text)

    snapshotter.attach(room, yroom.ydoc, write)
    await ws.accept()
    try:
        await websocket_server.serve(_FastAPIChannel(ws, room))
    finally:
        await snapshotter.detach(room, yroom.ydoc, write)
