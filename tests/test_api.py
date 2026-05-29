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
        first = alpha.receive_json()
        assert first["type"] == "presence"
        alpha.send_json({"x": 96, "y": 144, "skin_id": "player"})
        second = alpha.receive_json()
        assert second["players"][0]["pseudo"] == "Alpha"
        assert second["players"][0]["x"] == 96
