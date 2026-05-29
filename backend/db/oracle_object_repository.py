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
CHUNK_TILES = 8
TILE_SIZE = 48
CHUNK_PIXELS = CHUNK_TILES * TILE_SIZE

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
    chunk_coords = [
        (chunk_x, chunk_y)
        for chunk_y in range(center_y - 4, center_y + 5)
        for chunk_x in range(center_x - 4, center_x + 5)
    ]
    ensure_generated_resources_for_chunks(chunk_coords)
    resources_by_chunk = get_resources_for_chunks(chunk_coords)
    npcs_by_chunk = get_npcs_for_chunks(chunk_coords)
    chunks = [
        build_chunk(chunk_x, chunk_y, resources_by_chunk, npcs_by_chunk)
        for chunk_x, chunk_y in chunk_coords
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
    ensure_generated_resources(chunk_x, chunk_y)
    resources_by_chunk = {(chunk_x, chunk_y): get_resources_for_chunk(chunk_x, chunk_y)}
    npcs_by_chunk = {(chunk_x, chunk_y): get_npcs_for_chunk(chunk_x, chunk_y)}
    return build_chunk(chunk_x, chunk_y, resources_by_chunk, npcs_by_chunk)


def build_chunk(
    chunk_x: int,
    chunk_y: int,
    resources_by_chunk: dict[tuple[int, int], list[ResourceNode]],
    npcs_by_chunk: dict[tuple[int, int], list[NpcState]],
) -> ChunkState:
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
        tiles=generate_tiles(chunk_x, chunk_y),
        resources=resources_by_chunk.get((chunk_x, chunk_y), []),
        npcs=npcs_by_chunk.get((chunk_x, chunk_y), []),
        village=village,
    )


def generate_tiles(chunk_x: int, chunk_y: int) -> list[str]:
    tiles: list[str] = []
    for y in range(CHUNK_TILES):
        row = []
        for x in range(CHUNK_TILES):
            world_x = chunk_x * CHUNK_TILES + x
            world_y = chunk_y * CHUNK_TILES + y
            row.append(tile_code_at(world_x, world_y))
        tiles.append("".join(row))
    return tiles


def tile_code_at(world_x: int, world_y: int) -> str:
    river_left = river_left_x(world_y)
    river_width = river_tile_width(world_y)
    road_distance = road_distance_at(world_x, world_y)
    biome = biome_value(world_x, world_y)
    detail = deterministic_noise(world_x, world_y)

    if river_left <= world_x < river_left + river_width:
        return "w"
    if world_x in {river_left - 1, river_left + river_width}:
        return "v"
    if road_distance <= 0.42:
        return "d"
    if biome > 72:
        return "f" if detail % 7 == 0 else "g"
    if biome < 22:
        return "r" if detail % 5 else "v"
    if detail % 31 == 0:
        return "f"
    return "g"


def river_left_x(world_y: int) -> int:
    return round(
        18
        + math.sin(world_y * 0.09) * 8
        + math.sin(world_y * 0.023 + 1.7) * 22
        + math.sin(world_y * 0.011 - 0.4) * 34
    )


def river_tile_width(world_y: int) -> int:
    return 2 if deterministic_noise(37, world_y // 12) % 5 == 0 else 1


def road_distance_at(world_x: int, world_y: int) -> float:
    east_west_y = round(math.sin(world_x * 0.055) * 4 + math.sin(world_x * 0.017 + 2.1) * 9)
    north_south_x = round(math.sin(world_y * 0.061 + 0.8) * 5 + math.sin(world_y * 0.019) * 10)
    forest_trail_x = round(world_y * 0.42 + math.sin(world_y * 0.08) * 5 - 17)
    return min(
        abs(world_y - east_west_y),
        abs(world_x - north_south_x),
        abs(world_x - forest_trail_x),
    )


def biome_value(world_x: int, world_y: int) -> int:
    broad = smooth_noise(world_x / 22, world_y / 22)
    medium = smooth_noise(world_x / 9 + 18.4, world_y / 9 - 7.2)
    detail = smooth_noise(world_x / 4 - 11.1, world_y / 4 + 3.9)
    return round(broad * 58 + medium * 30 + detail * 12)


def smooth_noise(x: float, y: float) -> float:
    x0 = math.floor(x)
    y0 = math.floor(y)
    tx = smoothstep(x - x0)
    ty = smoothstep(y - y0)
    a = unit_noise(x0, y0)
    b = unit_noise(x0 + 1, y0)
    c = unit_noise(x0, y0 + 1)
    d = unit_noise(x0 + 1, y0 + 1)
    return lerp(lerp(a, b, tx), lerp(c, d, tx), ty)


def smoothstep(value: float) -> float:
    return value * value * (3 - 2 * value)


def lerp(start: float, end: float, amount: float) -> float:
    return start + (end - start) * amount


def unit_noise(x: int, y: int) -> float:
    return (deterministic_noise(x, y) % 10_000) / 9_999


def get_resources_for_chunk(chunk_x: int, chunk_y: int) -> list[ResourceNode]:
    min_x = chunk_x * CHUNK_PIXELS
    min_y = chunk_y * CHUNK_PIXELS
    max_x = min_x + CHUNK_PIXELS
    max_y = min_y + CHUNK_PIXELS
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


def get_resources_for_chunks(
    chunk_coords: list[tuple[int, int]],
) -> dict[tuple[int, int], list[ResourceNode]]:
    if not chunk_coords:
        return {}
    min_chunk_x = min(chunk_x for chunk_x, _chunk_y in chunk_coords)
    max_chunk_x = max(chunk_x for chunk_x, _chunk_y in chunk_coords)
    min_chunk_y = min(chunk_y for _chunk_x, chunk_y in chunk_coords)
    max_chunk_y = max(chunk_y for _chunk_x, chunk_y in chunk_coords)
    min_x = min_chunk_x * CHUNK_PIXELS
    min_y = min_chunk_y * CHUNK_PIXELS
    max_x = (max_chunk_x + 1) * CHUNK_PIXELS
    max_y = (max_chunk_y + 1) * CHUNK_PIXELS
    sql = """
        SELECT r.id, r.kind, r.x, r.y, r.amount
        FROM game_resource_nodes r
        WHERE r.x >= :min_x AND r.x < :max_x
          AND r.y >= :min_y AND r.y < :max_y
          AND r.amount > 0
        ORDER BY r.id
    """
    resources_by_chunk: dict[tuple[int, int], list[ResourceNode]] = {
        coord: [] for coord in chunk_coords
    }
    with oracle_connection() as connection, connection.cursor() as cursor:
        cursor.execute(sql, min_x=min_x, max_x=max_x, min_y=min_y, max_y=max_y)
        rows = cursor.fetchall()
    for row in rows:
        resource_id = str(row[0])
        x = int(row[2])
        y = int(row[3])
        if resource_id != resource_id_for_position(x, y):
            continue
        chunk = (x // CHUNK_PIXELS, y // CHUNK_PIXELS)
        if chunk not in resources_by_chunk:
            continue
        resources_by_chunk[chunk].append(
            ResourceNode(
                id=resource_id,
                kind=str(row[1]),
                x=x,
                y=y,
                amount=int(row[4]),
            )
        )
    return resources_by_chunk


def ensure_generated_resources(chunk_x: int, chunk_y: int) -> None:
    ensure_generated_resources_for_chunks([(chunk_x, chunk_y)])


def ensure_generated_resources_for_chunks(chunk_coords: list[tuple[int, int]]) -> None:
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
            for chunk_x, chunk_y in chunk_coords:
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
    origin_tile_x = chunk_x * CHUNK_TILES
    origin_tile_y = chunk_y * CHUNK_TILES
    for tile_y in range(CHUNK_TILES):
        for tile_x in range(CHUNK_TILES):
            world_x = origin_tile_x + tile_x
            world_y = origin_tile_y + tile_y
            tile = tile_code_at(world_x, world_y)
            seed = deterministic_noise(world_x, world_y)
            kind = resource_kind_for_tile(tile, world_x, world_y, seed)
            if kind is None:
                continue
            nodes.append(
                ResourceNode(
                    id=resource_id_for_tile(chunk_x, chunk_y, tile_x, tile_y),
                    kind=kind,
                    x=world_x * TILE_SIZE + 8 + (seed % 17),
                    y=world_y * TILE_SIZE + 10 + ((seed // 11) % 15),
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


def resource_id_for_position(x: int, y: int) -> str:
    world_x = x // TILE_SIZE
    world_y = y // TILE_SIZE
    chunk_x = world_x // CHUNK_TILES
    chunk_y = world_y // CHUNK_TILES
    tile_x = world_x - chunk_x * CHUNK_TILES
    tile_y = world_y - chunk_y * CHUNK_TILES
    return resource_id_for_tile(chunk_x, chunk_y, tile_x, tile_y)


def resource_id_for_tile(chunk_x: int, chunk_y: int, tile_x: int, tile_y: int) -> str:
    return f"gen-{chunk_x}-{chunk_y}-{tile_x}-{tile_y}"


def resource_amount(kind: str, seed: int) -> int:
    if kind == "tree":
        return 3 + seed % 5
    if kind == "ore":
        return 2 + seed % 4
    return 2 + seed % 6


def get_npcs_for_chunk(chunk_x: int, chunk_y: int) -> list[NpcState]:
    if chunk_x != 0 or chunk_y != 0:
        return []
    return get_npcs_for_chunks([(0, 0)]).get((0, 0), [])


def get_npcs_for_chunks(
    chunk_coords: list[tuple[int, int]],
) -> dict[tuple[int, int], list[NpcState]]:
    npcs_by_chunk: dict[tuple[int, int], list[NpcState]] = {coord: [] for coord in chunk_coords}
    if (0, 0) not in npcs_by_chunk:
        return npcs_by_chunk
    sql = """
        SELECT n.id, n.display_name, n.role, n.x, n.y, n.quest_marker
        FROM game_npcs n
        ORDER BY n.id
    """
    with oracle_connection() as connection, connection.cursor() as cursor:
        cursor.execute(sql)
        rows = cursor.fetchall()
    npcs_by_chunk[(0, 0)] = [
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
    return npcs_by_chunk


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
