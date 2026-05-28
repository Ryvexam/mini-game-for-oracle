from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.db.connection import get_oracle_settings, oracle_connection

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
def health() -> dict[str, object]:
    settings = get_oracle_settings()
    try:
        with oracle_connection() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM dual")
            cursor.fetchone()
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="Oracle est obligatoire pour lancer le jeu. Vérifie localhost:1521/FREEPDB1.",
        ) from exc

    return {
        "status": "ok",
        "oracle_available": True,
        "oracle_service": settings.dsn,
        "warning": None,
    }
