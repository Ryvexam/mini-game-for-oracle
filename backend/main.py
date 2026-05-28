from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.api import routes_game, routes_health, routes_oracle
from backend.db.connection import load_env_file

ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = ROOT / "frontend"
ASSETS_DIR = ROOT / "assets"

load_env_file(ROOT / ".env")


def allowed_origins() -> list[str]:
    raw = os.environ.get("ALLOWED_ORIGINS", "http://127.0.0.1:8000,http://localhost:8000")
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


app = FastAPI(title="Aventure Objet Oracle", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Accept"],
)

app.include_router(routes_health.router)
app.include_router(routes_oracle.router)
app.include_router(routes_game.router)

app.mount("/src", StaticFiles(directory=FRONTEND_DIR / "src"), name="src")
app.mount("/styles", StaticFiles(directory=FRONTEND_DIR / "styles"), name="styles")
app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")
