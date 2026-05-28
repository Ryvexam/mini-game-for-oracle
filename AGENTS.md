# Oracle Object Adventure Agent Notes

## Project Overview

Oracle Object Adventure is a multiplayer 2D Canvas sandbox game backed by Oracle
Object-Relational gameplay logic. Players join with a pseudo, explore generated
chunks, harvest resources, talk to NPCs, and complete gameplay plus SQL quests.

The app uses Oracle at `localhost:1521/FREEPDB1` or the `oracle` compose service.
Credentials must come from environment variables or a local `.env` file that is
never committed. Oracle is mandatory; there is no local gameplay fallback.

## Stack

- Backend: FastAPI.
- Database: direct `python-oracledb`; no ORM.
- Frontend: vanilla JavaScript modules and HTML5 Canvas.
- Assets: Codex image generation skill plus Pillow processing scripts.
- Tests: pytest.
- Lint: ruff.

## Commands

- Install: `pip install -e ".[dev]"`
- Verify raw generated concept assets: `python scripts/generate_concept_assets.py`
- Build production PNG assets: `python scripts/process_assets.py`
- Build GIF previews: `python scripts/generate_gifs.py`
- Build hatch-pet animated NPC atlases: `python scripts/build_hatch_pet_mascot.py`
- Start full stack: `docker compose up --build`
- Initialize Oracle schema: `curl -X POST http://127.0.0.1:8000/api/oracle/init-schema`
- Seed Oracle world: `curl -X POST http://127.0.0.1:8000/api/oracle/seed`
- Start app: `uvicorn backend.main:app --reload`
- Run tests: `pytest`
- Run lint: `ruff check .`

## Repository Governance

- Current working branch: `feat/oracle-object-adventure`.
- This local repository has no remote configured, so branch protection cannot be verified yet.
- Do not commit directly to `main` or `dev` once those branches exist.

## Security Rules

- Never commit `.env`, passwords, tokens, private keys, dumps, or credentials.
- Never use an ORM in this project.
- Use bind variables for all user-provided Oracle SQL values.
- Do not expose raw Oracle exceptions to the frontend.
- Keep CORS restricted outside development.

## Project Decisions

- Raw generated concept sheets live in `assets/generated/raw/`.
- Final runtime assets live in `assets/generated/`.
- Every player/NPC character has both a Canvas sprite sheet/GIF and a hatch-pet validated atlas under `assets/generated/hatch-pet/final/<character-id>/`.
- The game must not simulate gameplay locally if Oracle is unavailable.
- Oracle schema scripts use real object types, subtypes, type bodies, object
  tables, and package functions for player movement, harvesting, and SQL
  challenge resolution.

## Known Pitfalls

- The Oracle script splitter must ignore SQL*Plus directives only outside
  statements. Do not strip `SET` lines inside PL/SQL blocks; they are required
  for `UPDATE ... SET ...` statements in package bodies.
