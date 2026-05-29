"""Pre-render a large world map PNG (1 pixel per tile) using the deterministic
tile generator. Run in background; output goes to frontend/public/world-map.png."""
from __future__ import annotations

import sys
import time
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.db.oracle_object_repository import (  # noqa: E402
    TILE_SIZE,
    load_world_seed,
    tile_code_at,
)

load_world_seed()  # render with the currently persisted world seed

TILE_COLORS = {
    "g": (82, 125, 61),
    "p": (201, 176, 122),
    "w": (31, 127, 148),
    "r": (111, 111, 102),
    "f": (106, 163, 67),
    "v": (141, 135, 115),
    "d": (155, 116, 71),
    "s": (185, 189, 196),
}
FALLBACK = (54, 81, 60)

HALF = 1000
SIZE = HALF * 2 + 1  # -1000..+1000 inclusive, centered on block 0,0
ORIGIN_X = -HALF
ORIGIN_Y = -HALF

OUT = ROOT / "frontend" / "public" / "world-map.png"


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (SIZE, SIZE), FALLBACK)
    px = img.load()
    start = time.time()
    for ty in range(SIZE):
        world_y = ORIGIN_Y + ty
        for tx in range(SIZE):
            code = tile_code_at(ORIGIN_X + tx, world_y)
            px[tx, ty] = TILE_COLORS.get(code, FALLBACK)
        if ty % 100 == 0:
            print(f"row {ty}/{SIZE} ({time.time() - start:.1f}s)", flush=True)
    img.save(OUT)
    print(f"saved {OUT} origin=({ORIGIN_X},{ORIGIN_Y}) {SIZE}x{SIZE} in {time.time() - start:.1f}s", flush=True)


if __name__ == "__main__":
    main()
