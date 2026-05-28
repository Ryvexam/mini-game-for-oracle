from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.db import oracle_object_repository as repository

router = APIRouter(prefix="/api/oracle", tags=["oracle"])


@router.post("/init-schema")
def init_schema() -> dict[str, object]:
    try:
        count = repository.init_schema()
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "L'initialisation du schéma Oracle a échoué. "
                "Vérifie les logs serveur et les identifiants."
            ),
        ) from exc
    return {"ok": True, "statements_executed": count}


@router.post("/seed")
def seed() -> dict[str, object]:
    try:
        count = repository.seed_world_objects()
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Le chargement des données Oracle a échoué. "
                "Initialise d'abord le schéma et vérifie les identifiants."
            ),
        ) from exc
    return {"ok": True, "statements_executed": count}
