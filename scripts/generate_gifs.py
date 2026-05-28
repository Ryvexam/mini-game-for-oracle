from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPRITE_DIR = ROOT / "assets" / "generated" / "sprites"
HATCH_FINAL_DIR = ROOT / "assets" / "generated" / "hatch-pet" / "final"

SIGNATURE_GIFS = {
    "player": "running-right",
    "living_being": "idle",
    "human": "review",
    "monkey": "jumping",
    "lynx": "running-left",
    "oracle_sage": "waving",
    "ref_spirit": "waiting",
    "collection_keeper": "running",
    "final_guardian": "failed",
}


def main() -> None:
    for pet_id, state in SIGNATURE_GIFS.items():
        source = HATCH_FINAL_DIR / pet_id / "previews" / f"{state}.gif"
        if not source.exists():
            raise FileNotFoundError(
                f"Missing hatch-pet preview for {pet_id}. "
                "Run scripts/build_hatch_pet_mascot.py first."
            )
        target = SPRITE_DIR / f"{pet_id}.gif"
        shutil.copy2(source, target)
        print(f"wrote {target.relative_to(ROOT)} from {source.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
