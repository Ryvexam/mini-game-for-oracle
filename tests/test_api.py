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
