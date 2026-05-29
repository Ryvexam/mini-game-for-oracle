<div align="center">

# 🏝️ Oracle Object Adventure

### A multiplayer 2D sandbox powered entirely by Oracle Object-Relational features

> ⚡ **Made in 5 hours** using **GPT-5.5 in Codex** and **Opus 4.8**.

*All game logic lives in the database — object types, inheritance, polymorphism, packages, triggers and analytic views. Python only orchestrates.*

<br>

![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Oracle](https://img.shields.io/badge/Oracle_DB-F80000?style=for-the-badge&logo=oracle&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black)
![HTML5 Canvas](https://img.shields.io/badge/HTML5_Canvas-E34F26?style=for-the-badge&logo=html5&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)

![Python](https://img.shields.io/badge/python-3.11+-blue?style=flat-square&logo=python&logoColor=white)
![Tests](https://img.shields.io/badge/tests-pytest-0A9EDC?style=flat-square&logo=pytest&logoColor=white)
![Lint](https://img.shields.io/badge/lint-ruff-D7FF64?style=flat-square)
![No ORM](https://img.shields.io/badge/ORM-none_·_raw_PL%2FSQL-red?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)

</div>

---

## ✨ Overview

`oracle-object-adventure` is a multiplayer 2D sandbox game backed by **Oracle Object-Relational** features. Players join with a pseudo, get a visible nameplate and skin, explore an effectively infinite chunked world, harvest resources, talk to NPCs, and complete gameplay **and** SQL quests.

> **Oracle is mandatory.** There is no local gameplay fallback — every game rule lives inside the database.

The whole point of the project: demonstrate **object types, inheritance, polymorphism, encapsulation, object tables, packages, triggers and analytic views** in a real, interactive application. See **[`ORACLE.md`](ORACLE.md)** for the full schema walkthrough (with UML diagrams). Press **`P`** in-game for the same guide.

---

## 🧰 Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | FastAPI (REST + WebSocket) |
| **Frontend** | Vanilla JavaScript + HTML5 Canvas (no framework) |
| **Database** | Oracle on `localhost:1521/FREEPDB1` |
| **DB access** | `python-oracledb`, **raw SQL & PL/SQL only — no ORM**, bind variables everywhere |
| **Assets** | Codex image generation, hatch-pet atlases, Pillow processing |
| **Tooling** | `pytest` (tests) · `ruff` (lint) |

---

## 🚀 Quick Start

### With Docker

```bash
cp .env.example .env
docker compose up --build
```

Initialize the Oracle Object schema and seed data:

```bash
curl -X POST http://127.0.0.1:8000/api/oracle/init-schema
curl -X POST http://127.0.0.1:8000/api/oracle/seed
```

Open **[http://127.0.0.1:8000](http://127.0.0.1:8000)** and play.

### Local development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn backend.main:app --reload
```

`.env` must point at a real Oracle database:

```env
ORACLE_DSN=localhost:1521/FREEPDB1
ORACLE_USER=oracle_game
ORACLE_PASSWORD=change_this_password
```

> ⚠️ Never commit `.env`.

---

## 🎮 Gameplay

- Pseudo prompt at launch — player state is **loaded or created in Oracle**.
- Other players move live over WebSocket, interpolated and animated, with their pseudo above their sprite.
- Harvest resources with `E`; NPCs hand out quests.
- SQL questions use **real Oracle Object snippets**, answered with `1`, `2`, or `3`.
- Inventory and stats are persisted in Oracle.

### ⌨️ Controls

| Key | Action |
|-----|--------|
| `ZQSD` / Arrows | Move |
| `E` | Harvest / talk |
| `Enter` or `T` | Open chat (`Enter` to send, `Esc` to cancel) |
| `Tab` or `M` | Toggle stats + leaderboard menu |
| `C` | Open the world map |
| `1` / `2` / `3` | Answer the active SQL challenge |
| `P` | Open the in-game guide & UML schema |

> **Admin:** type `/regenmap` in chat (reserved pseudo) to reroll the world seed and reset everyone's stats.

---

## 🌟 Features

- **🗺️ Organic procedural world** — multi-octave value noise with domain warping drives elevation and moisture, producing forests, plains, rocky highlands, mountains and meandering rivers. Resources cluster by biome. Seeded and reproducible.
- **🌐 Live multiplayer** — WebSocket presence with auto-reconnect/backoff, a heartbeat, join/leave system messages and in-world chat bubbles. Remote players are position-interpolated for smooth movement.
- **🧭 Minimap** — biome-coloured, shows the camera viewport box plus village, NPC, resource and player markers.
- **🌗 Day/night cycle** — a four-minute lighting cycle overlays the world.
- **📊 Statistics via SQL triggers** — Oracle triggers populate `game_player_stats`; a `game_leaderboard` view ranks players via `RANK()`.

---

## 🧬 Oracle Object Model

```
entity_t  «NOT FINAL»
 ├── player_t   (UNDER entity_t · OVERRIDING move_to · gain_resource)
 └── npc_t      (UNDER entity_t)
resource_node_t · chest_t · action_result_t
```

The schema defines object types, object tables (`OF type_t`), a logic package and triggers:

- `entity_t`, `player_t UNDER entity_t`, `npc_t UNDER entity_t` — **inheritance & polymorphism**
- `resource_node_t`, `chest_t`, `action_result_t` — **encapsulation** (`TYPE BODY`)
- `game_actions_pkg` — the only write gate, centralizing `FOR UPDATE` locks

Gameplay actions call object methods and package functions:

```sql
player_t.move_to / player_t.gain_resource
resource_node_t.harvest_amount
game_actions_pkg.harvest_resource / answer_sql_challenge / move_player
```

### 📈 Statistics & SQL Triggers

`game_player_stats` is maintained **entirely by database triggers** (no application-side counting):

| Trigger | Event | Effect |
|---------|-------|--------|
| `trg_player_stats_create` | `AFTER INSERT` | Seeds a stats row on player insert |
| `trg_player_stats_resources` | `AFTER UPDATE OF wood, stone, ore` | Accumulates gathered totals + harvest count |
| `trg_player_stats_distance` | `AFTER UPDATE OF x, y` | Adds walked distance |
| `trg_player_stats_sql` | `AFTER INSERT OR UPDATE` | Counts SQL attempts and correct answers |

`game_leaderboard` ranks players by total resources via `RANK() OVER (...)`.

📖 Full details with diagrams: **[`ORACLE.md`](ORACLE.md)** · Asset generation spec: **[`TEXTURES.md`](TEXTURES.md)**

---

## 🎨 Asset Pipeline

Player and NPC skins are generated as hatch-pet style animated familiars. Raw generated sprite grids live under `assets/generated/raw/pet_atlases/`.

```bash
python scripts/generate_concept_assets.py
python scripts/process_assets.py
python scripts/build_hatch_pet_mascot.py
python scripts/generate_gifs.py
```

`build_hatch_pet_mascot.py` cuts generated 6×8 atlas grids and uses the installed `hatch-pet` skill scripts to build validated animated pet atlases.

---

## ✅ Checks

```bash
ruff check .
pytest
```

---

<div align="center">

Built with **Oracle Object-Relational** features · FastAPI · HTML5 Canvas

</div>
