from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
RAW_PET_DIR = ROOT / "assets" / "generated" / "raw" / "pet_atlases"
SPRITE_DIR = ROOT / "assets" / "generated" / "sprites"
HATCH_ROOT = ROOT / "assets" / "generated" / "hatch-pet"
FINAL_ROOT = HATCH_ROOT / "final"
SKILL_DIR = Path.home() / ".codex" / "skills" / "hatch-pet"

GRID_COLUMNS = 6
GRID_ROWS = 8
CANVAS_FRAME_SIZE = 48
PET_CELL_SIZE = (192, 208)

PETS = {
    "player": {
        "name": "Explorateur de l'Ile",
        "description": "Familier explorateur qui guide le joueur sur l'Ile des Objets Oracle.",
        "signature": "running-right",
    },
    "living_being": {
        "name": "LivingBeing",
        "description": "Familier supertype qui represente la racine commune des etres vivants.",
        "signature": "idle",
    },
    "human": {
        "name": "Sous-type Human",
        "description": "Familier humain qui explique l'heritage et les methodes redefinies.",
        "signature": "review",
    },
    "monkey": {
        "name": "Sous-type Monkey",
        "description": "Familier singe mobile pour les lecons de polymorphisme.",
        "signature": "jumping",
    },
    "lynx": {
        "name": "Sous-type Lynx",
        "description": "Familier lynx precis qui suit l'identite des objets.",
        "signature": "running-left",
    },
    "oracle_sage": {
        "name": "Sage Oracle",
        "description": "Familier sage qui enseigne les exemples SQL objet Oracle.",
        "signature": "waving",
    },
    "ref_spirit": {
        "name": "Esprit REF",
        "description": "Familier spectral qui explique REF et DEREF.",
        "signature": "waiting",
    },
    "collection_keeper": {
        "name": "Gardien des Collections",
        "description": "Familier gardien des VARRAY et des tables imbriquees.",
        "signature": "running",
    },
    "final_guardian": {
        "name": "Gardien FINAL",
        "description": "Familier gardien qui protege FINAL et NOT FINAL.",
        "signature": "failed",
    },
}

PET_STATE_ROWS = {
    "idle": (0, 6),
    "running-right": (3, 8),
    "running-left": (2, 8),
    "waving": (5, 4),
    "jumping": (7, 5),
    "failed": (6, 8),
    "waiting": (6, 6),
    "running": (7, 6),
    "review": (6, 6),
}

CANVAS_DIRECTION_ROWS = {
    "down": 1,
    "left": 2,
    "right": 3,
    "up": 4,
}


def ensure_output_dirs() -> None:
    HATCH_ROOT.mkdir(parents=True, exist_ok=True)
    SPRITE_DIR.mkdir(parents=True, exist_ok=True)
    if FINAL_ROOT.exists():
        shutil.rmtree(FINAL_ROOT)
    FINAL_ROOT.mkdir(parents=True, exist_ok=True)


def remove_chroma_key(image: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    pixels = rgba.load()
    for y in range(rgba.height):
        for x in range(rgba.width):
            r, g, b, a = pixels[x, y]
            if g > 145 and r < 120 and b < 130:
                pixels[x, y] = (0, 0, 0, 0)
            elif a > 0:
                pixels[x, y] = (r, g, b, 255)
    return rgba


def fit_to_canvas(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    cleaned = remove_chroma_key(image)
    bbox = cleaned.getbbox()
    if bbox:
        cleaned = cleaned.crop(bbox)
    max_width = int(size[0] * 0.82)
    max_height = int(size[1] * 0.82)
    scale = min(max_width / cleaned.width, max_height / cleaned.height, 1)
    resized = cleaned.resize(
        (max(1, int(cleaned.width * scale)), max(1, int(cleaned.height * scale))),
        Image.Resampling.LANCZOS,
    )
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    x = (size[0] - resized.width) // 2
    y = (size[1] - resized.height) // 2
    canvas.alpha_composite(resized, (x, y))
    return canvas


def extract_grid_frames(pet_id: str) -> list[list[Image.Image]]:
    source = RAW_PET_DIR / f"{pet_id}_grid.png"
    if not source.exists():
        raise FileNotFoundError(source)

    atlas = Image.open(source).convert("RGBA")
    cell_width = atlas.width // GRID_COLUMNS
    cell_height = atlas.height // GRID_ROWS
    rows: list[list[Image.Image]] = []
    for row in range(GRID_ROWS):
        frames = []
        for column in range(GRID_COLUMNS):
            box = (
                column * cell_width,
                row * cell_height,
                (column + 1) * cell_width,
                (row + 1) * cell_height,
            )
            frames.append(atlas.crop(box))
        rows.append(frames)
    return rows


def write_canvas_sheet(pet_id: str, rows: list[list[Image.Image]]) -> None:
    sheet = Image.new(
        "RGBA",
        (CANVAS_FRAME_SIZE * 4, CANVAS_FRAME_SIZE * 4),
        (0, 0, 0, 0),
    )
    for target_row, source_row_name in enumerate(["down", "left", "right", "up"]):
        source_row = rows[CANVAS_DIRECTION_ROWS[source_row_name]]
        for column in range(4):
            frame = fit_to_canvas(source_row[column], (CANVAS_FRAME_SIZE, CANVAS_FRAME_SIZE))
            sheet.alpha_composite(
                frame,
                (column * CANVAS_FRAME_SIZE, target_row * CANVAS_FRAME_SIZE),
            )
    sheet.save(SPRITE_DIR / f"{pet_id}_sheet.png")


def write_pet_frames(pet_id: str, rows: list[list[Image.Image]], frames_root: Path) -> None:
    if frames_root.exists():
        shutil.rmtree(frames_root)

    for state, (source_row_index, count) in PET_STATE_ROWS.items():
        state_dir = frames_root / state
        state_dir.mkdir(parents=True, exist_ok=True)
        source_row = rows[source_row_index]
        for index in range(count):
            source_frame = source_row[index % len(source_row)]
            frame = fit_to_canvas(source_frame, PET_CELL_SIZE)
            frame.save(state_dir / f"{index:02d}.png")


def run_hatch_pet_script(name: str, *args: str) -> None:
    script = SKILL_DIR / "scripts" / name
    subprocess.run([sys.executable, str(script), *args], cwd=ROOT, check=True)


def write_manifest(pet_id: str, config: dict[str, str], final_dir: Path) -> None:
    manifest = {
        "id": pet_id,
        "displayName": config["name"],
        "description": config["description"],
        "spritesheetPath": "spritesheet.webp",
    }
    (final_dir / "pet.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def export_signature_gif(pet_id: str, signature: str, final_dir: Path) -> None:
    source = final_dir / "previews" / f"{signature}.gif"
    if not source.exists():
        raise FileNotFoundError(source)
    shutil.copy2(source, SPRITE_DIR / f"{pet_id}.gif")


def build_pet(pet_id: str, config: dict[str, str]) -> None:
    rows = extract_grid_frames(pet_id)
    write_canvas_sheet(pet_id, rows)

    run_dir = HATCH_ROOT / pet_id
    frames_root = run_dir / "frames"
    final_dir = FINAL_ROOT / pet_id
    final_dir.mkdir(parents=True, exist_ok=True)
    write_pet_frames(pet_id, rows, frames_root)

    run_hatch_pet_script(
        "compose_atlas.py",
        "--frames-root",
        str(frames_root),
        "--output",
        str(final_dir / "spritesheet.png"),
        "--webp-output",
        str(final_dir / "spritesheet.webp"),
    )
    run_hatch_pet_script(
        "validate_atlas.py",
        str(final_dir / "spritesheet.png"),
        "--json-out",
        str(final_dir / "validation.json"),
    )
    run_hatch_pet_script(
        "make_contact_sheet.py",
        str(final_dir / "spritesheet.png"),
        "--output",
        str(final_dir / "contact-sheet.png"),
        "--scale",
        "0.5",
    )
    run_hatch_pet_script(
        "render_animation_previews.py",
        "--frames-root",
        str(frames_root),
        "--output-dir",
        str(final_dir / "previews"),
    )
    export_signature_gif(pet_id, config["signature"], final_dir)
    write_manifest(pet_id, config, final_dir)
    print(f"hatch-pet familiar ready from generated atlas: {final_dir.relative_to(ROOT)}")


def main() -> None:
    ensure_output_dirs()
    for pet_id, config in PETS.items():
        build_pet(pet_id, config)


if __name__ == "__main__":
    main()
