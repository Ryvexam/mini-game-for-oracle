from __future__ import annotations

from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.db.oracle_object_repository import SKINS, validate_pseudo

router = APIRouter(tags=["multiplayer"])


class PresenceHub:
    def __init__(self) -> None:
        self.connections: dict[str, WebSocket] = {}
        self.players: dict[str, dict[str, Any]] = {}

    async def connect(self, pseudo: str, skin_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self.connections[pseudo] = websocket
        self.players[pseudo] = {"pseudo": pseudo, "skin_id": skin_id, "x": 0, "y": 0}
        await self.broadcast()

    async def disconnect(self, pseudo: str) -> None:
        self.connections.pop(pseudo, None)
        self.players.pop(pseudo, None)
        await self.broadcast()

    async def update(self, pseudo: str, payload: dict[str, Any]) -> None:
        player = self.players.get(pseudo)
        if player is None:
            return
        player["x"] = int(payload.get("x", player["x"]))
        player["y"] = int(payload.get("y", player["y"]))
        skin_id = str(payload.get("skin_id", player["skin_id"]))
        if skin_id in SKINS:
            player["skin_id"] = skin_id
        await self.broadcast()

    async def broadcast(self) -> None:
        stale = []
        snapshot = {"type": "presence", "players": list(self.players.values())}
        for pseudo, websocket in self.connections.items():
            try:
                await websocket.send_json(snapshot)
            except RuntimeError:
                stale.append(pseudo)
        for pseudo in stale:
            self.connections.pop(pseudo, None)
            self.players.pop(pseudo, None)


presence_hub = PresenceHub()


@router.websocket("/ws/game")
async def game_socket(websocket: WebSocket) -> None:
    pseudo = websocket.query_params.get("pseudo", "")
    skin_id = websocket.query_params.get("skin_id", "player")
    try:
        validate_pseudo(pseudo)
    except ValueError:
        await websocket.close(code=1008)
        return
    if skin_id not in SKINS:
        skin_id = "player"

    await presence_hub.connect(pseudo, skin_id, websocket)
    try:
        while True:
            payload = await websocket.receive_json()
            await presence_hub.update(pseudo, payload)
    except WebSocketDisconnect:
        await presence_hub.disconnect(pseudo)
