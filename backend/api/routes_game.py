from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from backend.db import oracle_object_repository as repository
from backend.models.game import (
    ActionRequest,
    ActionResult,
    MoveRequest,
    PlayerSessionRequest,
    PlayerState,
    SqlAnswerRequest,
    TalkRequest,
    WorldState,
)

router = APIRouter(prefix="/api/game", tags=["game"])


def oracle_unavailable(exc: Exception) -> HTTPException:
    return HTTPException(
        status_code=503,
        detail="Oracle est obligatoire pour lancer le jeu. Vérifie localhost:1521/FREEPDB1.",
    )


@router.post("/session", response_model=PlayerState)
def create_session(request: PlayerSessionRequest) -> PlayerState:
    try:
        return repository.create_or_get_player(request.pseudo, request.skin_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise oracle_unavailable(exc) from exc


@router.get("/world", response_model=WorldState)
def world(
    pseudo: str = Query(min_length=3, max_length=24, pattern=r"^[\w-]+$"),
    chunk_x: int = 0,
    chunk_y: int = 0,
) -> WorldState:
    try:
        return repository.get_world_state(pseudo, chunk_x, chunk_y)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise oracle_unavailable(exc) from exc


@router.post("/move", response_model=PlayerState)
def move(request: MoveRequest) -> PlayerState:
    try:
        return repository.move_player(request.pseudo, request.x, request.y)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise oracle_unavailable(exc) from exc


@router.post("/harvest", response_model=ActionResult)
def harvest(request: ActionRequest) -> ActionResult:
    try:
        return repository.harvest_resource(request.pseudo, request.target_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise oracle_unavailable(exc) from exc


@router.post("/talk", response_model=ActionResult)
def talk(request: TalkRequest) -> ActionResult:
    try:
        return repository.talk_to_npc(request.pseudo, request.npc_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise oracle_unavailable(exc) from exc


@router.post("/sql-answer", response_model=ActionResult)
def answer_sql(request: SqlAnswerRequest) -> ActionResult:
    try:
        return repository.answer_sql_challenge(
            request.pseudo,
            request.challenge_id,
            request.answer_index,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise oracle_unavailable(exc) from exc
