# Oracle Object Adventure

`oracle-object-adventure` is a multiplayer 2D sandbox game backed by Oracle
Object-Relational features. Players join with a pseudo, get a visible nameplate
and skin, explore an effectively infinite chunked world, harvest resources, talk
to NPCs, and complete gameplay plus SQL quests.

Oracle is mandatory. The game does not provide a local gameplay fallback.

## Stack

- Backend: FastAPI
- Frontend: vanilla JavaScript + HTML5 Canvas
- Database: Oracle on `localhost:1521/FREEPDB1`
- Database access: `python-oracledb`, raw SQL and PL/SQL only
- Assets: Codex image generation, hatch-pet atlases, Pillow processing
- Tests: pytest
- Lint: ruff

## Run With Docker

```bash
cp .env.example .env
docker compose up --build
```

Then initialize the Oracle Object schema:

```bash
curl -X POST http://127.0.0.1:8000/api/oracle/init-schema
curl -X POST http://127.0.0.1:8000/api/oracle/seed
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000).

## Development Against Oracle

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn backend.main:app --reload
```

`.env` must point to a real Oracle database:

```env
ORACLE_DSN=localhost:1521/FREEPDB1
ORACLE_USER=oracle_game
ORACLE_PASSWORD=change_this_password
```

Do not commit `.env`.

## Gameplay

- Pseudo prompt at launch.
- Player state is loaded or created in Oracle.
- Other players are shown with their pseudo above their sprite.
- Resources can be harvested with `E`.
- NPCs at spawn provide quests.
- SQL questions use real Oracle Object snippets and are answered with `1`, `2`,
  or `3`.
- Inventory resources are persisted in Oracle.

## Oracle Object Model

The schema defines:

- `entity_t`
- `player_t UNDER entity_t`
- `npc_t UNDER entity_t`
- `resource_node_t`
- `action_result_t`
- `game_actions_pkg`

Gameplay actions use object methods and package functions such as:

- `player_t.move_to`
- `player_t.gain_resource`
- `resource_node_t.harvest_amount`
- `game_actions_pkg.harvest_resource`
- `game_actions_pkg.answer_sql_challenge`

## Asset Pipeline

The player and NPC skins are generated as hatch-pet style animated familiars.
Raw generated sprite grids live under `assets/generated/raw/pet_atlases/`.

```bash
python scripts/generate_concept_assets.py
python scripts/process_assets.py
python scripts/build_hatch_pet_mascot.py
python scripts/generate_gifs.py
```

`build_hatch_pet_mascot.py` cuts generated 6x8 atlas grids and uses the
installed `hatch-pet` skill scripts to build validated animated pet atlases.

## Checks

```bash
ruff check .
pytest
```
