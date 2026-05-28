from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "assets" / "generated" / "raw"

CONCEPTS = {
    "characters_concept.png": {
        "description": "3x3 generated character concept sheet.",
        "assets": [
            "player character",
            "LivingBeing NPC",
            "Human NPC",
            "Monkey NPC",
            "Lynx NPC",
            "Oracle Sage NPC",
            "Ref Spirit NPC",
            "Collection Keeper NPC",
            "Final Guardian NPC",
        ],
        "prompt": (
            "Create a coherent 3x3 concept sheet of nine cute readable "
            "fantasy-tech animal/NPC characters for Oracle Object Island."
        ),
    },
    "world_concept.png": {
        "description": "Generated terrain and object concept sheet.",
        "assets": [
            "grass tile",
            "dirt tile",
            "stone tile",
            "water tile",
            "path tile",
            "tree object",
            "rock object",
            "Type Forge building/object",
            "REF Bridge object",
            "Collection Chest object",
            "Final Gate object",
        ],
        "prompt": (
            "Create a coherent concept sheet for Oracle Object Island terrain "
            "tiles and map objects."
        ),
    },
    "ui_concept.png": {
        "description": "Generated UI concept sheet.",
        "assets": [
            "dialogue box UI",
            "Oracle icon UI",
            "interaction prompt UI",
        ],
        "prompt": "Create three coherent fantasy-tech Oracle Object Island UI assets with no text.",
    },
}


def validate_raw_assets() -> list[str]:
    missing = []
    for filename in CONCEPTS:
        path = RAW_DIR / filename
        if not path.exists():
            missing.append(filename)
            continue
        with Image.open(path) as image:
            image.verify()
    return missing


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path = RAW_DIR / "concept_manifest.json"
    manifest_path.write_text(json.dumps(CONCEPTS, indent=2), encoding="utf-8")

    missing = validate_raw_assets()
    if missing:
        missing_list = ", ".join(missing)
        raise SystemExit(
            "Missing raw generated concept sheets: "
            f"{missing_list}. Generate them with the Codex image generation skill using "
            f"the prompts in {manifest_path}."
        )

    print(f"concept assets ready: {manifest_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
