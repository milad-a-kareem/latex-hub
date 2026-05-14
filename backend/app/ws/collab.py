"""Yjs collaboration WebSocket endpoint.

We use pycrdt-websocket's in-memory ``YRoom`` per (projectId, filePath). For
production durability you'd back rooms with Firestore writes on debounce; for
the MVP we just keep state in memory and rely on clients to push updates.
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status
from pycrdt import Doc
from pycrdt_websocket import WebsocketServer, YRoom
from pycrdt_websocket.websocket import Websocket as PycrdtWS

from ..firebase import verify_id_token

router = APIRouter()
_server = WebsocketServer(auto_clean_rooms=False)


class _FastAPIWS:
    """Adapter exposing FastAPI's WebSocket as the protocol pycrdt-websocket expects."""

    def __init__(self, ws: WebSocket, path: str) -> None:
        self._ws = ws
        self.path = path

    async def send(self, message: bytes) -> None:
        await self._ws.send_bytes(message)

    async def recv(self) -> bytes:
        return await self._ws.receive_bytes()

    def __aiter__(self) -> AsyncIterator[bytes]:
        return self._iter()

    async def _iter(self) -> AsyncIterator[bytes]:
        try:
            while True:
                yield await self._ws.receive_bytes()
        except WebSocketDisconnect:
            return


@asynccontextmanager
async def _room(name: str) -> AsyncIterator[YRoom]:
    room = await _server.get_room(name)
    if room.ydoc is None:
        room.ydoc = Doc()
    yield room


@router.websocket("/ws/collab")
async def collab_ws(ws: WebSocket, token: str = Query(default=""), room: str = Query(...)) -> None:
    try:
        verify_id_token(token)
    except Exception:  # noqa: BLE001
        await ws.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    await ws.accept()
    adapter: PycrdtWS = _FastAPIWS(ws, room)  # type: ignore[assignment]
    async with _room(room) as yroom:
        await _server.serve(adapter, yroom)
