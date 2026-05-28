from __future__ import annotations

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_ASSETS = [
    "assets/generated/raw/characters_concept.png",
    "assets/generated/raw/world_concept.png",
    "assets/generated/raw/ui_concept.png",
    "assets/generated/sprites/player_sheet.png",
    "assets/generated/sprites/player.gif",
    "assets/generated/sprites/living_being_sheet.png",
    "assets/generated/sprites/living_being.gif",
    "assets/generated/sprites/human_sheet.png",
    "assets/generated/sprites/human.gif",
    "assets/generated/sprites/monkey_sheet.png",
    "assets/generated/sprites/monkey.gif",
    "assets/generated/sprites/lynx_sheet.png",
    "assets/generated/sprites/lynx.gif",
    "assets/generated/sprites/oracle_sage_sheet.png",
    "assets/generated/sprites/oracle_sage.gif",
    "assets/generated/sprites/ref_spirit_sheet.png",
    "assets/generated/sprites/ref_spirit.gif",
    "assets/generated/sprites/collection_keeper_sheet.png",
    "assets/generated/sprites/collection_keeper.gif",
    "assets/generated/sprites/final_guardian_sheet.png",
    "assets/generated/sprites/final_guardian.gif",
    "assets/generated/tiles/grass.png",
    "assets/generated/tiles/dirt.png",
    "assets/generated/tiles/stone.png",
    "assets/generated/tiles/water.png",
    "assets/generated/tiles/path.png",
    "assets/generated/tiles/path_straight.png",
    "assets/generated/tiles/path_corner.png",
    "assets/generated/tiles/path_t.png",
    "assets/generated/tiles/path_cross.png",
    "assets/generated/tiles/gravel.png",
    "assets/generated/tiles/rocky.png",
    "assets/generated/tiles/flower_grass.png",
    "assets/generated/objects/tree.png",
    "assets/generated/objects/rock.png",
    "assets/generated/objects/type_forge.png",
    "assets/generated/objects/method_dojo.png",
    "assets/generated/objects/object_village.png",
    "assets/generated/objects/poly_arena.png",
    "assets/generated/objects/ref_bridge.png",
    "assets/generated/objects/collection_chest.png",
    "assets/generated/objects/final_gate.png",
    "assets/generated/ui/dialog_box.png",
    "assets/generated/ui/oracle_icon.png",
    "assets/generated/ui/interaction_prompt.png",
]

HATCH_PETS = [
    "player",
    "living_being",
    "human",
    "monkey",
    "lynx",
    "oracle_sage",
    "ref_spirit",
    "collection_keeper",
    "final_guardian",
]

PET_ATLAS_ASSETS = [
    f"assets/generated/raw/pet_atlases/{pet_id}_grid.png" for pet_id in HATCH_PETS
]


def test_required_assets_exist_and_open() -> None:
    for relative_path in [*REQUIRED_ASSETS, *PET_ATLAS_ASSETS]:
        path = ROOT / relative_path
        assert path.exists(), relative_path
        if path.suffix.lower() in {".png", ".gif", ".webp"}:
            with Image.open(path) as image:
                image.verify()


def test_sprite_sheets_have_expected_size() -> None:
    for path in (ROOT / "assets/generated/sprites").glob("*_sheet.png"):
        with Image.open(path) as image:
            assert image.size == (192, 192)


def test_hatch_pet_outputs_exist_for_every_character() -> None:
    for pet_id in HATCH_PETS:
        pet_dir = ROOT / "assets" / "generated" / "hatch-pet" / "final" / pet_id
        for filename in ["spritesheet.webp", "spritesheet.png", "pet.json", "contact-sheet.png"]:
            assert (pet_dir / filename).exists(), f"missing {pet_id}/{filename}"


def test_character_gifs_are_hatch_pet_sized() -> None:
    for pet_id in HATCH_PETS:
        with Image.open(ROOT / "assets" / "generated" / "sprites" / f"{pet_id}.gif") as image:
            assert image.size == (192, 208)
            assert getattr(image, "n_frames", 1) >= 4
