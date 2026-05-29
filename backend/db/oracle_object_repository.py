from __future__ import annotations

import math
import re
import secrets
from pathlib import Path

from backend.db.connection import oracle_connection
from backend.models.game import (
    ActionResult,
    Chest,
    ChunkState,
    LeaderboardEntry,
    NpcState,
    OtherPlayer,
    PlayerState,
    PlayerStats,
    QuestState,
    QuestStep,
    ResourceNode,
    SqlChallenge,
    StatsResponse,
    WorldState,
)

DB_DIR = Path(__file__).resolve().parent
CHUNK_TILES = 8
TILE_SIZE = 48
CHUNK_PIXELS = CHUNK_TILES * TILE_SIZE

SKINS = ["player", "human", "monkey", "lynx", "oracle_sage", "collection_keeper"]

DEFAULT_WORLD_SEED = 0x45D9F3B
# Mutable world seed. All procedural generation funnels through
# deterministic_noise, so changing this re-rolls the entire map.
WORLD_SEED = DEFAULT_WORLD_SEED

# Linear chain of quests. Each step is "actionable"; a synthetic "done" step is
# appended only for display. Advancement rolls to the next quest in the list,
# which makes the finished quest disappear from the player's HUD.
QUEST_CATALOG: list[dict] = [
    {
        "id": "oracle-village-initiation",
        "title": "Initiation du Village Oracle",
        "giver": "sage-oracle",
        "steps": [
            {"kind": "talk", "target_id": "sage-oracle", "text": "Va parler au Sage Oracle."},
            {"kind": "harvest", "text": "Récolte une ressource (arbre, roche ou filon)."},
            {"kind": "sql", "challenge_id": "obj-method", "text": "Réponds au défi SQL du Sage."},
        ],
    },
    {
        "id": "bucheron-luma",
        "title": "Le bûcheron de Luma",
        "giver": "mineur-luma",
        "steps": [
            {"kind": "talk", "target_id": "mineur-luma", "text": "Parle à Luma la mineuse."},
            {
                "kind": "harvest",
                "required_item": "wood",
                "required_count": 5,
                "text": "Récolte 5 bois sur des arbres.",
            },
            {"kind": "sql", "challenge_id": "obj-inherit", "text": "Défi SQL : héritage d'objet."},
        ],
    },
    {
        "id": "mineur-de-fond",
        "title": "Mineur de fond",
        "giver": "mineur-luma",
        "steps": [
            {
                "kind": "harvest",
                "required_item": "ore",
                "required_count": 4,
                "text": "Extrais 4 minerais dans les montagnes.",
            },
            {"kind": "sql", "challenge_id": "obj-table", "text": "Défi SQL : table d'objets."},
        ],
    },
    {
        "id": "gardien-coffre",
        "title": "Le coffre du gardien",
        "giver": "marchand-moki",
        "steps": [
            {"kind": "talk", "target_id": "marchand-moki", "text": "Parle à Moki le marchand."},
            {"kind": "deposit", "text": "Dépose des objets dans un coffre."},
            {"kind": "sql", "challenge_id": "obj-body", "text": "Défi SQL : corps de type objet."},
        ],
    },
    {
        "id": "maitre-oracle",
        "title": "Maître Oracle",
        "giver": "sage-oracle",
        "steps": [
            {
                "kind": "harvest",
                "required_item": "stone",
                "required_count": 6,
                "text": "Taille 6 pierres dans les hauteurs rocheuses.",
            },
            {"kind": "sql", "challenge_id": "obj-ref", "text": "Défi SQL : VALUE() d'objet."},
        ],
    },
    {
        "id": "constructeur-objet",
        "title": "Le constructeur d'objets",
        "giver": "sage-oracle",
        "steps": [
            {"kind": "talk", "target_id": "sage-oracle", "text": "Retourne voir le Sage Oracle."},
            {
                "kind": "sql",
                "challenge_id": "obj-constructor",
                "text": "Défi SQL : constructeur d'objet.",
            },
        ],
    },
    {
        "id": "tri-des-objets",
        "title": "Le tri des objets",
        "giver": "mineur-luma",
        "steps": [
            {"kind": "talk", "target_id": "mineur-luma", "text": "Parle à Luma la mineuse."},
            {
                "kind": "harvest",
                "required_item": "wood",
                "required_count": 8,
                "text": "Récolte 8 bois pour Luma.",
            },
            {"kind": "sql", "challenge_id": "obj-map", "text": "Défi SQL : méthode MAP de tri."},
        ],
    },
    {
        "id": "suivre-la-ref",
        "title": "Suivre la référence",
        "giver": "marchand-moki",
        "steps": [
            {"kind": "talk", "target_id": "marchand-moki", "text": "Parle à Moki le marchand."},
            {"kind": "deposit", "text": "Dépose des objets dans un coffre."},
            {"kind": "sql", "challenge_id": "obj-deref", "text": "Défi SQL : DEREF d'une REF."},
        ],
    },
    {
        "id": "collection-ressources",
        "title": "Collection de ressources",
        "giver": "mineur-luma",
        "steps": [
            {
                "kind": "harvest",
                "required_item": "ore",
                "required_count": 6,
                "text": "Extrais 6 minerais pour la collection.",
            },
            {"kind": "sql", "challenge_id": "obj-coll", "text": "Défi SQL : collection d'objets."},
        ],
    },
    {
        "id": "methode-statique",
        "title": "La méthode statique",
        "giver": "sage-oracle",
        "steps": [
            {
                "kind": "harvest",
                "required_item": "stone",
                "required_count": 8,
                "text": "Taille 8 pierres pour le Sage.",
            },
            {"kind": "sql", "challenge_id": "obj-static", "text": "Défi SQL : méthode STATIC."},
        ],
    },
]

QUEST_INDEX = {quest["id"]: position for position, quest in enumerate(QUEST_CATALOG)}
FIRST_QUEST_ID = QUEST_CATALOG[0]["id"]


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
        or upper.startswith("DECLARE")
        or " TYPE BODY " in upper
        or upper.startswith("CREATE OR REPLACE PACKAGE ")
        or upper.startswith("CREATE OR REPLACE PACKAGE BODY ")
        or "CREATE OR REPLACE TRIGGER " in upper
        or "CREATE TRIGGER " in upper
    ):
        # PL/SQL blocks must keep their terminating END; — do not strip it.
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
          :resource_kind := v_result.resource_kind;
          :amount := v_result.amount;
          COMMIT;
        END;
    """
    with oracle_connection() as connection, connection.cursor() as cursor:
        ok = cursor.var(int)
        message = cursor.var(str)
        resource_kind = cursor.var(str)
        amount = cursor.var(int)
        cursor.execute(
            sql,
            pseudo=pseudo,
            target_id=target_id,
            ok=ok,
            message=message,
            resource_kind=resource_kind,
            amount=amount,
        )
    succeeded = bool(int(ok.getvalue()))
    if succeeded:
        record_quest_progress(
            pseudo,
            {
                "kind": "harvest",
                "item": resource_kind.getvalue(),
                "amount": int(amount.getvalue() or 0),
            },
        )
    return ActionResult(
        ok=succeeded,
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
    correct = bool(int(ok.getvalue()))
    if correct:
        record_quest_progress(
            pseudo,
            {"kind": "sql", "challenge_id": challenge_id, "correct": True},
        )
    return ActionResult(
        ok=correct,
        message=str(message.getvalue()),
        player=get_player(pseudo),
        quest=get_quest(pseudo),
    )


def talk_to_npc(pseudo: str, npc_id: str) -> ActionResult:
    validate_pseudo(pseudo)
    validate_identifier(npc_id)
    record_quest_progress(pseudo, {"kind": "talk", "target_id": npc_id})
    messages = {
        "sage-oracle": "Le Sage Oracle te confie une mission : récolte une ressource.",
        "mineur-luma": "Luma : récolte du bois puis reviens parler SQL.",
        "marchand-moki": "Moki : dépose tes objets dans un coffre pour les sécuriser.",
    }
    message = messages.get(npc_id, "Ce PNJ n'a rien de spécial à dire pour le moment.")
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
        chests=get_chests(),
    )


def get_chests() -> list[Chest]:
    sql = """
        SELECT c.id, c.owner, c.x, c.y, c.wood, c.stone, c.ore
        FROM game_chests c
        ORDER BY c.id
    """
    with oracle_connection() as connection, connection.cursor() as cursor:
        cursor.execute(sql)
        rows = cursor.fetchall()
    return [
        Chest(
            id=str(row[0]),
            owner=str(row[1]) if row[1] is not None else "",
            x=int(row[2]),
            y=int(row[3]),
            wood=int(row[4]),
            stone=int(row[5]),
            ore=int(row[6]),
        )
        for row in rows
    ]


def deposit_resources(pseudo: str, chest_id: str) -> ActionResult:
    validate_pseudo(pseudo)
    validate_identifier(chest_id)
    sql = """
        DECLARE
          v_result action_result_t;
        BEGIN
          v_result := game_actions_pkg.deposit_resources(:pseudo, :chest_id);
          :ok := v_result.ok;
          :message := v_result.message;
          COMMIT;
        END;
    """
    with oracle_connection() as connection, connection.cursor() as cursor:
        ok = cursor.var(int)
        message = cursor.var(str)
        cursor.execute(sql, pseudo=pseudo, chest_id=chest_id, ok=ok, message=message)
    succeeded = bool(int(ok.getvalue()))
    if succeeded:
        record_quest_progress(pseudo, {"kind": "deposit"})
    return ActionResult(
        ok=succeeded,
        message=str(message.getvalue()),
        player=get_player(pseudo),
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


def get_map_region(center_tile_x: int, center_tile_y: int, radius: int) -> dict:
    radius = max(10, min(140, radius))
    rows: list[str] = []
    for tile_y in range(center_tile_y - radius, center_tile_y + radius + 1):
        row = [
            tile_code_at(tile_x, tile_y)
            for tile_x in range(center_tile_x - radius, center_tile_x + radius + 1)
        ]
        rows.append("".join(row))
    return {
        "origin_x": center_tile_x - radius,
        "origin_y": center_tile_y - radius,
        "radius": radius,
        "rows": rows,
    }


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

    # Rivers and their gravel banks are carved first so water is always coherent.
    if river_left <= world_x < river_left + river_width:
        return "w"
    if world_x in {river_left - 1, river_left + river_width}:
        return "v"

    if road_distance_at(world_x, world_y) <= 0.42:
        return "d"

    elev = elevation(world_x, world_y)
    moist = moisture(world_x, world_y)
    detail = deterministic_noise(world_x, world_y)

    # Beaches hug the river: low elevation tiles next to the banks turn sandy/dry.
    if abs(world_x - river_left) <= 3 and elev < 0.40:
        return "v" if detail % 3 == 0 else "p"

    if elev > 0.70:
        return "s"  # mountain stone
    if elev > 0.57:
        return "r" if detail % 4 else "v"  # rocky highlands with gravel scree
    if moist > 0.62:
        return "f" if detail % 6 == 0 else "g"  # lush forest floor
    if moist < 0.27:
        return "r" if detail % 5 else "v"  # dry, stony badlands
    return "f" if detail % 29 == 0 else "g"  # plains with sparse flowers


def fbm(x: float, y: float, octaves: int = 4) -> float:
    total = 0.0
    amplitude = 1.0
    frequency = 1.0
    norm = 0.0
    for _ in range(octaves):
        total += amplitude * smooth_noise(x * frequency, y * frequency)
        norm += amplitude
        amplitude *= 0.5
        frequency *= 2.0
    return total / norm


def domain_warp(x: float, y: float) -> tuple[float, float]:
    warp_x = fbm(x * 0.5 + 5.2, y * 0.5 + 1.3, 2) - 0.5
    warp_y = fbm(x * 0.5 + 9.7, y * 0.5 + 8.1, 2) - 0.5
    return x + warp_x * 3.0, y + warp_y * 3.0


def seed_shift(salt: int) -> float:
    # Stable per-seed offset. Large value so biome/river/road sampling lands in a
    # completely different region of noise space for each world seed.
    return ((WORLD_SEED * 2654435761) >> (salt * 7 % 24) & 0xFFFF) * 0.37 + salt * 91.7


def elevation(world_x: int, world_y: int) -> float:
    wx, wy = domain_warp(world_x / 26.0 + seed_shift(1), world_y / 26.0 + seed_shift(2))
    ridged = abs(fbm(wx + 41.0, wy - 17.0, 3) - 0.5) * 2.0
    base = fbm(wx, wy, 5)
    return max(0.0, min(1.0, base * 0.7 + ridged * 0.3))


def moisture(world_x: int, world_y: int) -> float:
    mx = world_x / 34.0 + 100.0 + seed_shift(3)
    my = world_y / 34.0 - 60.0 + seed_shift(4)
    wx, wy = domain_warp(mx, my)
    return max(0.0, min(1.0, fbm(wx, wy, 4)))


def river_left_x(world_y: int) -> int:
    # Meandering river path built from layered sines plus organic noise jitter.
    # Seed-derived phase shifts move the meander so each world has a distinct river.
    p1 = seed_shift(5)
    p2 = seed_shift(6)
    jitter = (fbm(world_y / 30.0 + 3.0 + seed_shift(7), 0.5, 3) - 0.5) * 10.0
    return round(
        18
        + math.sin(world_y * 0.09 + p1) * 8
        + math.sin(world_y * 0.023 + 1.7 + p2) * 22
        + math.sin(world_y * 0.011 - 0.4 + p1) * 34
        + jitter
    )


def river_tile_width(world_y: int) -> int:
    return 2 if deterministic_noise(37, world_y // 12) % 5 == 0 else 1


def road_distance_at(world_x: int, world_y: int) -> float:
    p1 = seed_shift(8)
    p2 = seed_shift(9)
    east_west_y = round(
        math.sin(world_x * 0.055 + p1) * 4 + math.sin(world_x * 0.017 + 2.1 + p2) * 9
    )
    north_south_x = round(
        math.sin(world_y * 0.061 + 0.8 + p2) * 5 + math.sin(world_y * 0.019 + p1) * 10
    )
    forest_trail_x = round(world_y * 0.42 + math.sin(world_y * 0.08 + p1) * 5 - 17)
    return min(
        abs(world_y - east_west_y),
        abs(world_x - north_south_x),
        abs(world_x - forest_trail_x),
    )


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


# Chunks whose procedural resources were already MERGEd this process lifetime.
# Resources are persisted in Oracle, so re-running the MERGE on every world poll
# is pure overhead. Skip already-seeded chunks to keep fetches fast.
_ENSURED_CHUNKS: set[tuple[int, int]] = set()


def ensure_generated_resources_for_chunks(chunk_coords: list[tuple[int, int]]) -> None:
    pending = [coord for coord in chunk_coords if coord not in _ENSURED_CHUNKS]
    if not pending:
        return

    rows = [
        {
            "id": node.id,
            "kind": node.kind,
            "x": node.x,
            "y": node.y,
            "amount": node.amount,
        }
        for chunk_x, chunk_y in pending
        for node in generated_resources(chunk_x, chunk_y)
    ]

    if rows:
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
                cursor.executemany(sql, rows)
            connection.commit()

    _ENSURED_CHUNKS.update(pending)


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
    if tile in {"w", "p", "d"}:
        return None
    moist = moisture(world_x, world_y)
    elev = elevation(world_x, world_y)

    # Dense, clustered forests in wet lowlands; sparser groves elsewhere.
    if tile in {"g", "f"}:
        if moist > 0.74 and seed % 3 in {0, 1}:
            return "tree"
        if moist > 0.6 and seed % 5 == 0:
            return "tree"
        if moist > 0.45 and seed % 17 == 0:
            return "tree"

    # Ore concentrates in the mountains, rock litters the rocky highlands.
    if tile == "s":
        return "ore" if seed % 2 == 0 else "rock"
    if tile == "r" and seed % 3 == 0:
        return "ore" if (seed % 7 == 0 and elev > 0.6) else "rock"
    if tile == "v" and seed % 9 == 0:
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
    return get_npcs_for_chunks([(chunk_x, chunk_y)]).get((chunk_x, chunk_y), [])


def get_npcs_for_chunks(
    chunk_coords: list[tuple[int, int]],
) -> dict[tuple[int, int], list[NpcState]]:
    npcs_by_chunk: dict[tuple[int, int], list[NpcState]] = {coord: [] for coord in chunk_coords}
    sql = """
        SELECT n.id, n.display_name, n.role, n.x, n.y, n.quest_marker
        FROM game_npcs n
        ORDER BY n.id
    """
    with oracle_connection() as connection, connection.cursor() as cursor:
        cursor.execute(sql)
        rows = cursor.fetchall()
    for row in rows:
        x = int(row[3])
        y = int(row[4])
        chunk = (x // CHUNK_PIXELS, y // CHUNK_PIXELS)
        if chunk not in npcs_by_chunk:
            continue
        npcs_by_chunk[chunk].append(
            NpcState(
                id=str(row[0]),
                name=str(row[1]),
                role=str(row[2]),
                x=x,
                y=y,
                quest_marker=str(row[5]) if row[5] is not None else None,
            )
        )
    return npcs_by_chunk


def read_quest_row(pseudo: str) -> tuple[str, int, int] | None:
    sql = """
        SELECT quest_id, step_index, step_progress
        FROM game_player_quests
        WHERE pseudo = :pseudo
    """
    with oracle_connection() as connection, connection.cursor() as cursor:
        cursor.execute(sql, pseudo=pseudo)
        row = cursor.fetchone()
    if row is None:
        return None
    return str(row[0]), int(row[1]), int(row[2])


def get_sql_challenge(challenge_id: str) -> SqlChallenge | None:
    sql = """
        SELECT id, prompt, sql_code, choice_1, choice_2, choice_3
        FROM game_sql_challenges
        WHERE id = :challenge_id
    """
    with oracle_connection() as connection, connection.cursor() as cursor:
        cursor.execute(sql, challenge_id=challenge_id)
        row = cursor.fetchone()
    if row is None:
        return None
    return SqlChallenge(
        id=str(row[0]),
        prompt=str(row[1]),
        sql_code=str(row[2]),
        choices=[str(row[3]), str(row[4]), str(row[5])],
    )


def get_quest(pseudo: str) -> QuestState | None:
    row = read_quest_row(pseudo)
    if row is None:
        return None
    quest_id, step_index, step_progress = row
    position = QUEST_INDEX.get(quest_id, 0)
    quest = QUEST_CATALOG[position]
    actionable = quest["steps"]

    display_steps = [
        QuestStep(
            kind=step["kind"],
            target_id=step.get("target_id"),
            text=step["text"],
            required_item=step.get("required_item"),
            required_count=step.get("required_count", 0),
        )
        for step in actionable
    ]
    display_steps.append(QuestStep(kind="done", text="Quête terminée."))

    sql_challenge = None
    if 0 <= step_index < len(actionable):
        current = actionable[step_index]
        if current["kind"] == "sql":
            sql_challenge = get_sql_challenge(current["challenge_id"])

    giver_name = None
    giver_block_x = None
    giver_block_y = None
    giver_id = quest.get("giver")
    if giver_id:
        giver = get_npc(giver_id)
        if giver:
            giver_name = giver.name
            giver_block_x = giver.x // TILE_SIZE
            giver_block_y = giver.y // TILE_SIZE

    return QuestState(
        id=quest_id,
        title=quest["title"],
        step_index=step_index,
        step_progress=step_progress,
        quest_number=position + 1,
        total_quests=len(QUEST_CATALOG),
        giver_name=giver_name,
        giver_block_x=giver_block_x,
        giver_block_y=giver_block_y,
        steps=display_steps,
        sql_challenge=sql_challenge,
    )


def get_npc(npc_id: str) -> NpcState | None:
    sql = """
        SELECT n.id, n.display_name, n.role, n.x, n.y, n.quest_marker
        FROM game_npcs n
        WHERE n.id = :npc_id
    """
    with oracle_connection() as connection, connection.cursor() as cursor:
        cursor.execute(sql, npc_id=npc_id)
        row = cursor.fetchone()
    if row is None:
        return None
    return NpcState(
        id=str(row[0]),
        name=str(row[1]),
        role=str(row[2]),
        x=int(row[3]),
        y=int(row[4]),
        quest_marker=str(row[5]) if row[5] is not None else None,
    )


def enrich_player_with_quest(player: PlayerState) -> PlayerState:
    quest = get_quest(player.pseudo)
    if quest:
        player.current_quest_id = quest.id
        player.quest_step = quest.step_index
    return player


def record_quest_progress(pseudo: str, event: dict) -> None:
    """Advance the player's quest chain if the event satisfies the current step."""
    row = read_quest_row(pseudo)
    if row is None:
        return
    quest_id, step_index, step_progress = row
    position = QUEST_INDEX.get(quest_id, 0)
    actionable = QUEST_CATALOG[position]["steps"]
    if step_index < 0 or step_index >= len(actionable):
        return

    step = actionable[step_index]
    kind = step["kind"]
    if kind != event.get("kind"):
        return

    completed = False
    new_progress = step_progress

    if kind == "talk":
        completed = step.get("target_id") == event.get("target_id")
    elif kind == "harvest":
        required_item = step.get("required_item")
        if required_item is None:
            completed = True
        elif event.get("item") == required_item:
            new_progress = step_progress + int(event.get("amount", 0))
            completed = new_progress >= step.get("required_count", 0)
    elif kind == "sql":
        completed = event.get("correct") and step.get("challenge_id") == event.get("challenge_id")
    elif kind == "deposit":
        completed = True

    if not completed:
        if new_progress != step_progress:
            _set_quest(pseudo, quest_id, step_index, new_progress)
        return

    next_step = step_index + 1
    if next_step >= len(actionable) and position + 1 < len(QUEST_CATALOG):
        _set_quest(pseudo, QUEST_CATALOG[position + 1]["id"], 0, 0)
    else:
        _set_quest(pseudo, quest_id, next_step, 0)


def _set_quest(pseudo: str, quest_id: str, step_index: int, step_progress: int) -> None:
    sql = """
        UPDATE game_player_quests
        SET quest_id = :quest_id,
            step_index = :step_index,
            step_progress = :step_progress,
            updated_at = SYSTIMESTAMP
        WHERE pseudo = :pseudo
    """
    with oracle_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                sql,
                pseudo=pseudo,
                quest_id=quest_id,
                step_index=step_index,
                step_progress=step_progress,
            )
        connection.commit()


def get_stats(pseudo: str, limit: int = 10) -> StatsResponse:
    validate_pseudo(pseudo)
    player_sql = """
        SELECT pseudo, wood_gathered, stone_gathered, ore_gathered, harvest_actions,
               distance_moved, sql_attempts, sql_correct, total_gathered, rank_position
        FROM game_leaderboard
        WHERE pseudo = :pseudo
    """
    board_sql = """
        SELECT pseudo, total_gathered, ore_gathered, sql_correct, rank_position
        FROM game_leaderboard
        ORDER BY rank_position, pseudo
        FETCH FIRST :limit ROWS ONLY
    """
    with oracle_connection() as connection, connection.cursor() as cursor:
        cursor.execute(player_sql, pseudo=pseudo)
        player_row = cursor.fetchone()
        cursor.execute(board_sql, limit=limit)
        board_rows = cursor.fetchall()

    player = None
    if player_row is not None:
        player = PlayerStats(
            pseudo=str(player_row[0]),
            wood_gathered=int(player_row[1]),
            stone_gathered=int(player_row[2]),
            ore_gathered=int(player_row[3]),
            harvest_actions=int(player_row[4]),
            distance_moved=int(player_row[5]) // TILE_SIZE,
            sql_attempts=int(player_row[6]),
            sql_correct=int(player_row[7]),
            total_gathered=int(player_row[8]),
            rank_position=int(player_row[9]),
        )
    leaderboard = [
        LeaderboardEntry(
            pseudo=str(row[0]),
            total_gathered=int(row[1]),
            ore_gathered=int(row[2]),
            sql_correct=int(row[3]),
            rank_position=int(row[4]),
        )
        for row in board_rows
    ]
    return StatsResponse(player=player, leaderboard=leaderboard)


def deterministic_noise(x: int, y: int) -> int:
    return abs((x * 92837111) ^ (y * 689287499) ^ WORLD_SEED)


def load_world_seed() -> int:
    global WORLD_SEED
    try:
        with oracle_connection() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT seed FROM game_world_meta WHERE id = 1")
            row = cursor.fetchone()
    except Exception:
        return WORLD_SEED
    if row:
        WORLD_SEED = int(row[0])
    return WORLD_SEED


def regenerate_world(new_seed: int | None = None) -> int:
    """Pick a fresh seed, wipe generated terrain + everyone's stats, persist.

    Spawn-placed objects (NPCs, chests, hand-placed nodes) are kept; only the
    procedurally generated resource nodes are dropped so they re-roll with the
    new seed on the next world fetch.
    """
    global WORLD_SEED
    seed = int(new_seed) if new_seed is not None else secrets.randbelow(2_000_000_000) + 1

    with oracle_connection() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            MERGE INTO game_world_meta t USING (SELECT 1 id FROM dual) s ON (t.id = s.id)
            WHEN MATCHED THEN UPDATE SET seed = :seed
            WHEN NOT MATCHED THEN INSERT (id, seed) VALUES (1, :seed)
            """,
            seed=seed,
        )
        cursor.execute("DELETE FROM game_resource_nodes WHERE id LIKE 'gen-%'")
        cursor.execute(
            """
            UPDATE game_player_stats SET
              wood_gathered = 0,
              stone_gathered = 0,
              ore_gathered = 0,
              harvest_actions = 0,
              distance_moved = 0,
              sql_attempts = 0,
              sql_correct = 0,
              updated_at = SYSTIMESTAMP
            """
        )
        connection.commit()

    WORLD_SEED = seed
    _ENSURED_CHUNKS.clear()
    return seed


def validate_pseudo(value: str) -> None:
    if not re.fullmatch(r"[\w-]{3,24}", value):
        raise ValueError("invalid pseudo")


def validate_identifier(value: str) -> None:
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", value):
        raise ValueError("invalid identifier")


def distance(a_x: int, a_y: int, b_x: int, b_y: int) -> float:
    return math.hypot(a_x - b_x, a_y - b_y)
