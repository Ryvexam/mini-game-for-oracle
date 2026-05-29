from __future__ import annotations

import asyncio
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.db import oracle_object_repository as repo
from backend.db.oracle_object_repository import SKINS, validate_pseudo

router = APIRouter(tags=["multiplayer"])

DIRECTIONS = {"up", "down", "left", "right"}
MAX_CHAT_LEN = 120
WORLD_ADMIN = "Ryvexam"
_MAP_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "generate_world_map.py"


class PresenceHub:
    def __init__(self) -> None:
        self.connections: dict[str, WebSocket] = {}
        self.players: dict[str, dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, pseudo: str, skin_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self.connections[pseudo] = websocket
        self.players[pseudo] = {
            "pseudo": pseudo,
            "skin_id": skin_id,
            "x": 240,
            "y": 300,
            "direction": "down",
            "frame": 0,
            "moving": False,
        }
        await websocket.send_json({"type": "welcome", "pseudo": pseudo})
        await self.broadcast({"type": "system", "text": f"{pseudo} a rejoint l'aventure."})
        await self.broadcast_presence()

    async def disconnect(self, pseudo: str) -> None:
        self.connections.pop(pseudo, None)
        self.players.pop(pseudo, None)
        await self.broadcast({"type": "system", "text": f"{pseudo} a quitté l'aventure."})
        await self.broadcast_presence()

    async def update(self, pseudo: str, payload: dict[str, Any]) -> None:
        player = self.players.get(pseudo)
        if player is None:
            return
        player["x"] = int(payload.get("x", player["x"]))
        player["y"] = int(payload.get("y", player["y"]))
        player["moving"] = bool(payload.get("moving", False))
        direction = str(payload.get("direction", player["direction"]))
        if direction in DIRECTIONS:
            player["direction"] = direction
        frame = payload.get("frame", player["frame"])
        if isinstance(frame, int) and 0 <= frame < 8:
            player["frame"] = frame
        skin_id = str(payload.get("skin_id", player["skin_id"]))
        if skin_id in SKINS:
            player["skin_id"] = skin_id
        await self.broadcast_presence()

    async def chat(self, pseudo: str, payload: dict[str, Any]) -> None:
        text = str(payload.get("text", "")).strip()[:MAX_CHAT_LEN]
        if not text:
            return
        if text.startswith("/"):
            await self.handle_command(pseudo, text)
            return
        await self.broadcast(
            {"type": "chat", "pseudo": pseudo, "text": text, "ts": int(time.time())}
        )

    async def handle_command(self, pseudo: str, text: str) -> None:
        command = text.split()[0].lower()
        if command == "/regenmap":
            await self.regen_map(pseudo)
            return
        await self._notify(pseudo, f"Commande inconnue : {command}")

    async def regen_map(self, pseudo: str) -> None:
        if pseudo != WORLD_ADMIN:
            await self._notify(pseudo, "Seul Ryvexam peut régénérer la carte.")
            return
        seed = await asyncio.to_thread(repo.regenerate_world)
        # Re-render the static overview map with the new seed in the background.
        subprocess.Popen(  # noqa: S603
            [sys.executable, str(_MAP_SCRIPT)],
            cwd=str(_MAP_SCRIPT.parents[1]),
        )
        await self.broadcast(
            {"type": "system", "text": f"{pseudo} a régénéré le monde. Nouvelle seed appliquée."}
        )
        await self.broadcast({"type": "world_reset", "seed": seed})

    async def _notify(self, pseudo: str, text: str) -> None:
        websocket = self.connections.get(pseudo)
        if websocket is not None:
            await self._safe_send(websocket, {"type": "system", "text": text})

    async def broadcast_presence(self) -> None:
        await self.broadcast({"type": "presence", "players": list(self.players.values())})

    async def broadcast(self, message: dict[str, Any]) -> None:
        stale: list[str] = []
        targets = list(self.connections.items())
        results = await asyncio.gather(
            *(self._safe_send(ws, message) for _pseudo, ws in targets),
            return_exceptions=True,
        )
        for (pseudo, _ws), result in zip(targets, results, strict=False):
            if isinstance(result, Exception):
                stale.append(pseudo)
        for pseudo in stale:
            self.connections.pop(pseudo, None)
            self.players.pop(pseudo, None)

    @staticmethod
    async def _safe_send(websocket: WebSocket, message: dict[str, Any]) -> None:
        await websocket.send_json(message)


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

    if pseudo in presence_hub.connections:
        await websocket.accept()
        await websocket.send_json(
            {"type": "duplicate", "text": "Ce pseudo est déjà connecté."}
        )
        await websocket.close(code=4001)
        return

    await presence_hub.connect(pseudo, skin_id, websocket)
    try:
        while True:
            payload = await websocket.receive_json()
            message_type = payload.get("type", "move")
            if message_type == "chat":
                await presence_hub.chat(pseudo, payload)
            elif message_type == "ping":
                await websocket.send_json({"type": "pong"})
            else:
                await presence_hub.update(pseudo, payload)
    except WebSocketDisconnect:
        await presence_hub.disconnect(pseudo)
    except Exception:
        await presence_hub.disconnect(pseudo)
