"""Yjs collaboration WebSocket endpoint.

Each ``?room=<projectId:filePath>`` query maps to a ``YRoom`` held in memory
by ``pycrdt.websocket``'s :class:`WebsocketServer`. State is in-memory only;
on container scale-out or scale-down it is lost. For durability, hook
``room.ydoc.observe`` to debounce-write snapshots into Firestore.
"""

from __future__ import annotations

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status
from pycrdt.websocket import WebsocketServer

from ..firebase import verify_id_token

router = APIRouter()
websocket_server = WebsocketServer(auto_clean_rooms=False)


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


@router.websocket("/ws/collab")
async def collab_ws(
    ws: WebSocket,
    token: str = Query(default=""),
    room: str = Query(...),
) -> None:
    try:
        verify_id_token(token)
    except Exception:
        await ws.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    await ws.accept()
    await websocket_server.serve(_FastAPIChannel(ws, room))
