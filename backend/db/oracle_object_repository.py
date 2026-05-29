from __future__ import annotations

import math
import re
from pathlib import Path

from backend.db.connection import oracle_connection
from backend.models.game import (
    ActionResult,
    ChunkState,
    NpcState,
    OtherPlayer,
    PlayerState,
    QuestState,
    QuestStep,
    ResourceNode,
    SqlChallenge,
    WorldState,
)

DB_DIR = Path(__file__).resolve().parent

SKINS = ["player", "human", "monkey", "lynx", "oracle_sage", "collection_keeper"]
QUEST_ID = "oracle-village-initiation"
SQL_CHALLENGE = SqlChallenge(
    id="object-type-method",
    prompt="Dans ce type Oracle, quelle ligne déclare une méthode membre ?",
    sql_code="""CREATE TYPE resource_node_t AS OBJECT (
  id VARCHAR2(80),
  kind VARCHAR2(20),
  MEMBER FUNCTION harvest_amount RETURN NUMBER
) NOT FINAL;""",
    choices=[
        "kind VARCHAR2(20)",
        "MEMBER FUNCTION harvest_amount RETURN NUMBER",
        "NOT FINAL",
    ],
)


def split_oracle_script(script: str) -> list[str]:
    statements: list[str] = []
    buffer: list[str] = []

    for raw_line in script.splitlines():
        line = raw_line.rstrip()
        if not buffer and not line.strip():
            continue
        if line.strip() == "/":
            statement = normalize_oracle_statement("\n".join(buffer))
            if statement:
                statements.append(statement)
            buffer = []
            continue
        if not buffer and line.strip().upper().startswith(("PROMPT ", "SET ")):
            continue
        buffer.append(line)

    trailing = normalize_oracle_statement("\n".join(buffer))
    if trailing:
        statements.append(trailing)
    return statements


def normalize_oracle_statement(statement: str) -> str:
    cleaned = statement.strip()
    if not cleaned:
        return ""
    upper = cleaned.upper()
    if (
        upper.startswith("BEGIN")
        or " TYPE BODY " in upper
        or upper.startswith("CREATE OR REPLACE PACKAGE ")
        or upper.startswith("CREATE OR REPLACE PACKAGE BODY ")
    ):
        return cleaned
    return cleaned.rstrip(";")


def execute_script_file(path: Path) -> int:
    script = path.read_text(encoding="utf-8")
    statements = split_oracle_script(script)
    with oracle_connection() as connection:
        with connection.cursor() as cursor:
            for statement in statements:
                cursor.execute(statement)
        connection.commit()
    return len(statements)


def init_schema() -> int:
    return execute_script_file(DB_DIR / "schema.sql")


def seed_world_objects() -> int:
    return execute_script_file(DB_DIR / "seed.sql")


def create_or_get_player(pseudo: str, skin_id: str | None = None) -> PlayerState:
    validate_pseudo(pseudo)
    skin = skin_id if skin_id in SKINS else SKINS[hash(pseudo) % len(SKINS)]
    sql = """
        DECLARE
          v_player player_t;
        BEGIN
          v_player := game_actions_pkg.create_or_get_player(:pseudo, :skin_id);
          :x := v_player.x;
          :y := v_player.y;
          :skin_out := v_player.skin_id;
          :wood := v_player.wood;
          :stone := v_player.stone;
          :ore := v_player.ore;
          COMMIT;
        END;
    """
    with oracle_connection() as connection, connection.cursor() as cursor:
        x = cursor.var(int)
        y = cursor.var(int)
        skin_out = cursor.var(str)
        wood = cursor.var(int)
        stone = cursor.var(int)
        ore = cursor.var(int)
        cursor.execute(
            sql,
            pseudo=pseudo,
            skin_id=skin,
            x=x,
            y=y,
            skin_out=skin_out,
            wood=wood,
            stone=stone,
            ore=ore,
        )
    player = PlayerState(
        pseudo=pseudo,
        skin_id=str(skin_out.getvalue()),
        x=int(x.getvalue()),
        y=int(y.getvalue()),
        wood=int(wood.getvalue()),
        stone=int(stone.getvalue()),
        ore=int(ore.getvalue()),
    )
    return enrich_player_with_quest(player)


def move_player(pseudo: str, x: int, y: int) -> PlayerState:
    validate_pseudo(pseudo)
    sql = """
        DECLARE
          v_player player_t;
        BEGIN
          v_player := game_actions_pkg.move_player(:pseudo, :x_in, :y_in);
          :skin_out := v_player.skin_id;
          :wood := v_player.wood;
          :stone := v_player.stone;
          :ore := v_player.ore;
          COMMIT;
        END;
    """
    with oracle_connection() as connection, connection.cursor() as cursor:
        skin_out = cursor.var(str)
        wood = cursor.var(int)
        stone = cursor.var(int)
        ore = cursor.var(int)
        cursor.execute(
            sql,
            pseudo=pseudo,
            x_in=x,
            y_in=y,
            skin_out=skin_out,
            wood=wood,
            stone=stone,
            ore=ore,
        )
    player = PlayerState(
        pseudo=pseudo,
        skin_id=str(skin_out.getvalue()),
        x=x,
        y=y,
        wood=int(wood.getvalue()),
        stone=int(stone.getvalue()),
        ore=int(ore.getvalue()),
    )
    return enrich_player_with_quest(player)


def harvest_resource(pseudo: str, target_id: str) -> ActionResult:
    validate_pseudo(pseudo)
    validate_identifier(target_id)
    sql = """
        DECLARE
          v_result action_result_t;
        BEGIN
          v_result := game_actions_pkg.harvest_resource(:pseudo, :target_id);
          :ok := v_result.ok;
          :message := v_result.message;
          COMMIT;
        END;
    """
    with oracle_connection() as connection, connection.cursor() as cursor:
        ok = cursor.var(int)
        message = cursor.var(str)
        cursor.execute(sql, pseudo=pseudo, target_id=target_id, ok=ok, message=message)
    return ActionResult(
        ok=bool(int(ok.getvalue())),
        message=str(message.getvalue()),
        player=get_player(pseudo),
        quest=get_quest(pseudo),
    )


def answer_sql_challenge(pseudo: str, challenge_id: str, answer_index: int) -> ActionResult:
    validate_pseudo(pseudo)
    validate_identifier(challenge_id)
    sql = """
        DECLARE
          v_result action_result_t;
        BEGIN
          v_result := game_actions_pkg.answer_sql_challenge(:pseudo, :challenge_id, :answer_index);
          :ok := v_result.ok;
          :message := v_result.message;
          COMMIT;
        END;
    """
    with oracle_connection() as connection, connection.cursor() as cursor:
        ok = cursor.var(int)
        message = cursor.var(str)
        cursor.execute(
            sql,
            pseudo=pseudo,
            challenge_id=challenge_id,
            answer_index=answer_index,
            ok=ok,
            message=message,
        )
    return ActionResult(
        ok=bool(int(ok.getvalue())),
        message=str(message.getvalue()),
        player=get_player(pseudo),
        quest=get_quest(pseudo),
    )


def talk_to_npc(pseudo: str, npc_id: str) -> ActionResult:
    validate_pseudo(pseudo)
    validate_identifier(npc_id)
    if npc_id == "sage-oracle":
        advance_quest_if_step(pseudo, 0, 1)
        message = "Le Sage Oracle te confie une mission : récolte une ressource."
    elif npc_id == "mineur-luma":
        message = "Luma : mine une roche ou un filon, puis reviens parler SQL."
    else:
        message = "Ce PNJ n'a rien de spécial à dire pour le moment."
    return ActionResult(
        ok=True,
        message=message,
        player=get_player(pseudo),
        quest=get_quest(pseudo),
    )


def get_world_state(pseudo: str, center_x: int, center_y: int) -> WorldState:
    player = get_player(pseudo)
    chunks = [
        get_chunk(chunk_x, chunk_y)
        for chunk_y in range(center_y - 1, center_y + 2)
        for chunk_x in range(center_x - 1, center_x + 2)
    ]
    return WorldState(
        player=player,
        players=get_other_players(pseudo),
        chunks=chunks,
        quest=get_quest(pseudo),
    )


def get_player(pseudo: str) -> PlayerState:
    validate_pseudo(pseudo)
    sql = """
        SELECT p.id, p.skin_id, p.x, p.y, p.wood, p.stone, p.ore
        FROM game_players p
        WHERE p.id = :pseudo
    """
    with oracle_connection() as connection, connection.cursor() as cursor:
        cursor.execute(sql, pseudo=pseudo)
        row = cursor.fetchone()
    if row is None:
        return create_or_get_player(pseudo)
    player = PlayerState(
        pseudo=str(row[0]),
        skin_id=str(row[1]),
        x=int(row[2]),
        y=int(row[3]),
        wood=int(row[4]),
        stone=int(row[5]),
        ore=int(row[6]),
    )
    return enrich_player_with_quest(player)


def get_other_players(pseudo: str) -> list[OtherPlayer]:
    sql = """
        SELECT p.id, p.skin_id, p.x, p.y
        FROM game_players p
        WHERE p.id <> :pseudo
        ORDER BY p.id
        FETCH FIRST 20 ROWS ONLY
    """
    with oracle_connection() as connection, connection.cursor() as cursor:
        cursor.execute(sql, pseudo=pseudo)
        rows = cursor.fetchall()
    return [
        OtherPlayer(pseudo=str(row[0]), skin_id=str(row[1]), x=int(row[2]), y=int(row[3]))
        for row in rows
    ]


def get_chunk(chunk_x: int, chunk_y: int) -> ChunkState:
    tiles = generate_tiles(chunk_x, chunk_y)
    resources = get_resources_for_chunk(chunk_x, chunk_y)
    npcs = get_npcs_for_chunk(chunk_x, chunk_y)
    village = None
    if chunk_x == 0 and chunk_y == 0:
        village = {
            "name": "Village Oracle",
            "x": 260,
            "y": 240,
            "buildings": ["forge", "market"],
        }
    return ChunkState(
        chunk_x=chunk_x,
        chunk_y=chunk_y,
        tiles=tiles,
        resources=resources,
        npcs=npcs,
        village=village,
    )


def generate_tiles(chunk_x: int, chunk_y: int) -> list[str]:
    tiles: list[str] = []
    for y in range(16):
        row = []
        for x in range(16):
            world_x = chunk_x * 16 + x
            world_y = chunk_y * 16 + y
            row.append(tile_code_at(world_x, world_y))
        tiles.append("".join(row))
    return tiles


def tile_code_at(world_x: int, world_y: int) -> str:
    river_center = river_center_x(world_y)
    river_distance = abs(world_x - river_center)
    road_distance = min(abs(world_x), abs(world_y), abs(world_x - world_y // 2))
    biome = biome_value(world_x, world_y)
    detail = deterministic_noise(world_x, world_y)

    if river_distance <= river_width(world_y):
        return "w"
    if river_distance <= river_width(world_y) + 1:
        return "v"
    if road_distance <= 1:
        return "p"
    if road_distance == 2:
        return "d"
    if biome > 72:
        return "f" if detail % 7 == 0 else "g"
    if biome < 22:
        return "r" if detail % 5 else "v"
    if detail % 31 == 0:
        return "f"
    return "g"


def river_center_x(world_y: int) -> int:
    return round(
        18
        + math.sin(world_y * 0.09) * 8
        + math.sin(world_y * 0.023 + 1.7) * 22
        + math.sin(world_y * 0.011 - 0.4) * 34
    )


def river_width(world_y: int) -> int:
    return 1 + (deterministic_noise(37, world_y // 8) % 2)


def biome_value(world_x: int, world_y: int) -> int:
    coarse_x = math.floor(world_x / 10)
    coarse_y = math.floor(world_y / 10)
    local = deterministic_noise(coarse_x, coarse_y) % 100
    neighbor = deterministic_noise(coarse_x + 1, coarse_y - 1) % 100
    return (local * 3 + neighbor) // 4


def get_resources_for_chunk(chunk_x: int, chunk_y: int) -> list[ResourceNode]:
    ensure_generated_resources(chunk_x, chunk_y)
    min_x = chunk_x * 768
    min_y = chunk_y * 768
    max_x = min_x + 768
    max_y = min_y + 768
    sql = """
        SELECT r.id, r.kind, r.x, r.y, r.amount
        FROM game_resource_nodes r
        WHERE r.x >= :min_x AND r.x < :max_x
          AND r.y >= :min_y AND r.y < :max_y
          AND r.amount > 0
        ORDER BY r.id
    """
    with oracle_connection() as connection, connection.cursor() as cursor:
        cursor.execute(sql, min_x=min_x, max_x=max_x, min_y=min_y, max_y=max_y)
        rows = cursor.fetchall()
    return [
        ResourceNode(
            id=str(row[0]),
            kind=str(row[1]),
            x=int(row[2]),
            y=int(row[3]),
            amount=int(row[4]),
        )
        for row in rows
    ]


def ensure_generated_resources(chunk_x: int, chunk_y: int) -> None:
    sql = """
        MERGE INTO game_resource_nodes r
        USING (
          SELECT :id AS id,
                 :kind AS kind,
                 :x AS x,
                 :y AS y,
                 :amount AS amount
          FROM dual
        ) incoming
        ON (r.id = incoming.id)
        WHEN NOT MATCHED THEN INSERT
          VALUES (
            resource_node_t(
              incoming.id,
              incoming.kind,
              incoming.x,
              incoming.y,
              incoming.amount
            )
          )
    """
    with oracle_connection() as connection:
        with connection.cursor() as cursor:
            for node in generated_resources(chunk_x, chunk_y):
                cursor.execute(
                    sql,
                    id=node.id,
                    kind=node.kind,
                    x=node.x,
                    y=node.y,
                    amount=node.amount,
                )
        connection.commit()


def generated_resources(chunk_x: int, chunk_y: int) -> list[ResourceNode]:
    nodes = []
    origin_tile_x = chunk_x * 16
    origin_tile_y = chunk_y * 16
    for tile_y in range(16):
        for tile_x in range(16):
            world_x = origin_tile_x + tile_x
            world_y = origin_tile_y + tile_y
            tile = tile_code_at(world_x, world_y)
            seed = deterministic_noise(world_x, world_y)
            kind = resource_kind_for_tile(tile, world_x, world_y, seed)
            if kind is None:
                continue
            nodes.append(
                ResourceNode(
                    id=f"gen-{chunk_x}-{chunk_y}-{tile_x}-{tile_y}",
                    kind=kind,
                    x=world_x * 48 + 8 + (seed % 17),
                    y=world_y * 48 + 10 + ((seed // 11) % 15),
                    amount=resource_amount(kind, seed),
                )
            )
    return nodes


def resource_kind_for_tile(tile: str, world_x: int, world_y: int, seed: int) -> str | None:
    if tile == "w" or tile == "p" or tile == "d":
        return None
    forest_density = biome_value(world_x, world_y)
    if forest_density > 72 and seed % 5 in {0, 1, 2}:
        return "tree"
    if forest_density > 58 and seed % 17 == 0:
        return "tree"
    if tile == "r" and seed % 4 == 0:
        return "ore" if seed % 9 == 0 else "rock"
    if tile == "v" and seed % 13 == 0:
        return "rock"
    return None


def resource_amount(kind: str, seed: int) -> int:
    if kind == "tree":
        return 3 + seed % 5
    if kind == "ore":
        return 2 + seed % 4
    return 2 + seed % 6


def get_npcs_for_chunk(chunk_x: int, chunk_y: int) -> list[NpcState]:
    if chunk_x != 0 or chunk_y != 0:
        return []
    sql = """
        SELECT n.id, n.display_name, n.role, n.x, n.y, n.quest_marker
        FROM game_npcs n
        ORDER BY n.id
    """
    with oracle_connection() as connection, connection.cursor() as cursor:
        cursor.execute(sql)
        rows = cursor.fetchall()
    return [
        NpcState(
            id=str(row[0]),
            name=str(row[1]),
            role=str(row[2]),
            x=int(row[3]),
            y=int(row[4]),
            quest_marker=str(row[5]) if row[5] is not None else None,
        )
        for row in rows
    ]


def get_quest(pseudo: str) -> QuestState | None:
    sql = """
        SELECT quest_id, step_index
        FROM game_player_quests
        WHERE pseudo = :pseudo
    """
    with oracle_connection() as connection, connection.cursor() as cursor:
        cursor.execute(sql, pseudo=pseudo)
        row = cursor.fetchone()
    if row is None:
        return None
    step_index = int(row[1])
    return QuestState(
        id=str(row[0]),
        title="Initiation du Village Oracle",
        step_index=step_index,
        steps=[
            QuestStep(
                kind="talk",
                target_id="sage-oracle",
                text="Va parler au Sage Oracle.",
            ),
            QuestStep(
                kind="harvest",
                text="Récolte une ressource sur une roche, un arbre ou un filon.",
            ),
            QuestStep(kind="sql", text="Réponds à la question SQL du Sage Oracle."),
            QuestStep(kind="done", text="Quête terminée."),
        ],
        sql_challenge=SQL_CHALLENGE if step_index >= 2 else None,
    )


def enrich_player_with_quest(player: PlayerState) -> PlayerState:
    quest = get_quest(player.pseudo)
    if quest:
        player.current_quest_id = quest.id
        player.quest_step = quest.step_index
    return player


def advance_quest_if_step(pseudo: str, expected: int, next_step: int) -> None:
    sql = """
        UPDATE game_player_quests
        SET step_index = :next_step,
            updated_at = SYSTIMESTAMP
        WHERE pseudo = :pseudo
          AND step_index = :expected
    """
    with oracle_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql, pseudo=pseudo, expected=expected, next_step=next_step)
        connection.commit()


def deterministic_noise(x: int, y: int) -> int:
    return abs((x * 92837111) ^ (y * 689287499) ^ 0x45D9F3B)


def validate_pseudo(value: str) -> None:
    if not re.fullmatch(r"[\w-]{3,24}", value):
        raise ValueError("invalid pseudo")


def validate_identifier(value: str) -> None:
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", value):
        raise ValueError("invalid identifier")


def distance(a_x: int, a_y: int, b_x: int, b_y: int) -> float:
    return math.hypot(a_x - b_x, a_y - b_y)
