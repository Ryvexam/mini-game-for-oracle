from __future__ import annotations

from pydantic import BaseModel, Field


class PlayerSessionRequest(BaseModel):
    pseudo: str = Field(min_length=3, max_length=24, pattern=r"^[\w-]+$")
    skin_id: str | None = Field(default=None, max_length=40)


class MoveRequest(BaseModel):
    pseudo: str = Field(min_length=3, max_length=24, pattern=r"^[\w-]+$")
    x: int = Field(ge=-1_000_000, le=1_000_000)
    y: int = Field(ge=-1_000_000, le=1_000_000)


class ActionRequest(BaseModel):
    pseudo: str = Field(min_length=3, max_length=24, pattern=r"^[\w-]+$")
    target_id: str = Field(min_length=1, max_length=80)


class TalkRequest(BaseModel):
    pseudo: str = Field(min_length=3, max_length=24, pattern=r"^[\w-]+$")
    npc_id: str = Field(min_length=1, max_length=80)


class SqlAnswerRequest(BaseModel):
    pseudo: str = Field(min_length=3, max_length=24, pattern=r"^[\w-]+$")
    challenge_id: str = Field(min_length=1, max_length=80)
    answer_index: int = Field(ge=0, le=8)


class PlayerState(BaseModel):
    pseudo: str
    skin_id: str
    x: int
    y: int
    wood: int
    stone: int
    ore: int
    current_quest_id: str | None = None
    quest_step: int = 0


class OtherPlayer(BaseModel):
    pseudo: str
    skin_id: str
    x: int
    y: int


class ResourceNode(BaseModel):
    id: str
    kind: str
    x: int
    y: int
    amount: int


class NpcState(BaseModel):
    id: str
    name: str
    role: str
    x: int
    y: int
    quest_marker: str | None = None


class QuestStep(BaseModel):
    kind: str
    target_id: str | None = None
    text: str
    required_item: str | None = None
    required_count: int = 0


class SqlChallenge(BaseModel):
    id: str
    prompt: str
    sql_code: str
    choices: list[str]


class QuestState(BaseModel):
    id: str
    title: str
    step_index: int
    steps: list[QuestStep]
    sql_challenge: SqlChallenge | None = None


class ChunkState(BaseModel):
    chunk_x: int
    chunk_y: int
    tiles: list[str]
    resources: list[ResourceNode]
    npcs: list[NpcState]
    village: dict[str, object] | None = None


class WorldState(BaseModel):
    player: PlayerState
    players: list[OtherPlayer]
    chunks: list[ChunkState]
    quest: QuestState | None


class ActionResult(BaseModel):
    ok: bool
    message: str
    player: PlayerState
    quest: QuestState | None = None
