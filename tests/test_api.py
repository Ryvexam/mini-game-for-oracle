from __future__ import annotations

from fastapi.testclient import TestClient

from backend.main import app


def test_game_session_requires_valid_pseudo() -> None:
    client = TestClient(app)
    response = client.post("/api/game/session", json={"pseudo": "x"})
    assert response.status_code == 422


def test_game_session_accepts_french_pseudo_shape() -> None:
    client = TestClient(app)
    response = client.post("/api/game/session", json={"pseudo": "Renée-42"})
    assert response.status_code != 422


def test_frontend_index_is_served() -> None:
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "Entre ton pseudo" in response.text


def test_multiplayer_websocket_broadcasts_presence() -> None:
    client = TestClient(app)
    with client.websocket_connect("/ws/game?pseudo=Alpha&skin_id=player") as alpha:
        presence = receive_until(alpha, "presence")
        assert presence["players"][0]["pseudo"] == "Alpha"
        alpha.send_json({"type": "move", "x": 96, "y": 144, "skin_id": "player"})
        updated = receive_until(alpha, "presence")
        assert updated["players"][0]["x"] == 96


def receive_until(socket, message_type, attempts=8):
    for _ in range(attempts):
        message = socket.receive_json()
        if message.get("type") == message_type:
            return message
    raise AssertionError(f"no {message_type} message received")
