from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance

ROOT = Path(__file__).resolve().parents[1]
GENERATED_DIR = ROOT / "assets" / "generated"
RAW_DIR = GENERATED_DIR / "raw"
SPRITE_DIR = GENERATED_DIR / "sprites"
TILE_DIR = GENERATED_DIR / "tiles"
OBJECT_DIR = GENERATED_DIR / "objects"
UI_DIR = GENERATED_DIR / "ui"

CHARACTERS = [
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

TILES = ["grass", "dirt", "stone", "water", "path"]


@dataclass(frozen=True)
class CropSpec:
    name: str
    center_x: float
    center_y: float
    width: float
    height: float
    target_size: tuple[int, int]


OBJECT_SPECS = [
    CropSpec("tree", 0.115, 0.605, 0.20, 0.36, (96, 96)),
    CropSpec("rock", 0.305, 0.615, 0.19, 0.28, (80, 80)),
    CropSpec("type_forge", 0.500, 0.595, 0.22, 0.34, (128, 112)),
    CropSpec("ref_bridge", 0.690, 0.595, 0.24, 0.32, (128, 96)),
    CropSpec("collection_chest", 0.880, 0.595, 0.22, 0.27, (96, 80)),
    CropSpec("final_gate", 0.500, 0.885, 0.26, 0.27, (128, 112)),
]

UI_SPECS = [
    CropSpec("dialog_box", 0.255, 0.505, 0.50, 0.70, (640, 180)),
    CropSpec("oracle_icon", 0.645, 0.505, 0.22, 0.70, (96, 96)),
    CropSpec("interaction_prompt", 0.880, 0.505, 0.22, 0.62, (160, 80)),
]


def ensure_dirs() -> None:
    for directory in [SPRITE_DIR, TILE_DIR, OBJECT_DIR, UI_DIR]:
        directory.mkdir(parents=True, exist_ok=True)


def open_rgba(path: Path) -> Image.Image:
    if not path.exists():
        raise FileNotFoundError(path)
    return Image.open(path).convert("RGBA")


def remove_chroma_key(image: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    key = rgba.getpixel((0, 0))[:3]
    pixels = rgba.load()

    for y in range(rgba.height):
        for x in range(rgba.width):
            r, g, b, a = pixels[x, y]
            distance = ((r - key[0]) ** 2 + (g - key[1]) ** 2 + (b - key[2]) ** 2) ** 0.5
            green_screen = g > 170 and g > r + 35 and g > b + 35
            if distance < 105 or green_screen:
                pixels[x, y] = (0, 0, 0, 0)
            elif a > 0:
                pixels[x, y] = (r, g, b, 255)
    return rgba


def trim_alpha(image: Image.Image) -> Image.Image:
    box = image.getchannel("A").getbbox()
    if box is None:
        return image
    return image.crop(box)


def fit_to_canvas(image: Image.Image, size: tuple[int, int], padding: int = 2) -> Image.Image:
    image = trim_alpha(image)
    target_w, target_h = size
    if image.width == 0 or image.height == 0:
        return Image.new("RGBA", size, (0, 0, 0, 0))

    ratio = min((target_w - padding * 2) / image.width, (target_h - padding * 2) / image.height)
    resized = image.resize(
        (max(1, int(image.width * ratio)), max(1, int(image.height * ratio))),
        Image.Resampling.NEAREST,
    )
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    x = (target_w - resized.width) // 2
    y = (target_h - resized.height) // 2
    canvas.alpha_composite(resized, (x, y))
    return canvas


def crop_relative(image: Image.Image, spec: CropSpec) -> Image.Image:
    width = int(image.width * spec.width)
    height = int(image.height * spec.height)
    center_x = int(image.width * spec.center_x)
    center_y = int(image.height * spec.center_y)
    left = max(0, center_x - width // 2)
    top = max(0, center_y - height // 2)
    right = min(image.width, left + width)
    bottom = min(image.height, top + height)
    return image.crop((left, top, right, bottom))


def make_direction_sprite(sprite: Image.Image, direction: str) -> Image.Image:
    if direction == "left":
        return sprite.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    if direction == "right":
        return sprite
    if direction == "up":
        back = sprite.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        return ImageEnhance.Brightness(ImageEnhance.Color(back).enhance(0.82)).enhance(0.9)
    return sprite


def make_walk_sheet(base_sprite: Image.Image) -> Image.Image:
    frame_size = 48
    sheet = Image.new("RGBA", (frame_size * 4, frame_size * 4), (0, 0, 0, 0))
    directions = ["down", "left", "right", "up"]
    offsets = [(-1, 1), (0, -1), (1, 1), (0, 0)]

    for row, direction in enumerate(directions):
        direction_sprite = make_direction_sprite(base_sprite, direction)
        for col, (offset_x, offset_y) in enumerate(offsets):
            frame = Image.new("RGBA", (frame_size, frame_size), (0, 0, 0, 0))
            shifted = direction_sprite
            if col == 1:
                shifted = ImageEnhance.Brightness(shifted).enhance(1.04)
            frame.alpha_composite(shifted, (offset_x, offset_y))
            sheet.alpha_composite(frame, (col * frame_size, row * frame_size))
    return sheet


def process_characters() -> None:
    concept = remove_chroma_key(open_rgba(RAW_DIR / "characters_concept.png"))
    cell_w = concept.width // 3
    cell_h = concept.height // 3

    for index, name in enumerate(CHARACTERS):
        col = index % 3
        row = index // 3
        cell = concept.crop((col * cell_w, row * cell_h, (col + 1) * cell_w, (row + 1) * cell_h))
        sprite = fit_to_canvas(cell, (48, 48), padding=4)
        sheet = make_walk_sheet(sprite)
        sheet.save(SPRITE_DIR / f"{name}_sheet.png")


def process_tiles() -> None:
    concept = open_rgba(RAW_DIR / "world_concept.png")
    cell_w = concept.width // 5
    tile_crop_h = int(concept.height * 0.36)
    for index, name in enumerate(TILES):
        cell = concept.crop((index * cell_w, 0, (index + 1) * cell_w, tile_crop_h))
        clean = remove_chroma_key(cell)
        tile = fit_to_canvas(clean, (48, 48), padding=0)
        tile.save(TILE_DIR / f"{name}.png")

    make_texture_variant(TILE_DIR / "dirt.png", TILE_DIR / "gravel.png", "gravel")
    make_texture_variant(TILE_DIR / "stone.png", TILE_DIR / "rocky.png", "rocky")
    make_texture_variant(TILE_DIR / "grass.png", TILE_DIR / "flower_grass.png", "flowers")
    process_path_variants()


def process_objects() -> None:
    concept = remove_chroma_key(open_rgba(RAW_DIR / "world_concept.png"))
    for spec in OBJECT_SPECS:
        cropped = crop_relative(concept, spec)
        fit_to_canvas(cropped, spec.target_size, padding=2).save(OBJECT_DIR / f"{spec.name}.png")

    make_building_variant(
        "type_forge",
        "method_dojo",
        tint=(0.78, 0.92, 1.12),
        banner=(38, 87, 130),
    )
    make_building_variant(
        "type_forge",
        "object_village",
        tint=(1.08, 0.96, 0.82),
        banner=(146, 83, 45),
    )
    make_building_variant(
        "final_gate",
        "poly_arena",
        tint=(1.05, 0.88, 1.12),
        banner=(112, 55, 132),
    )


def process_ui() -> None:
    concept = remove_chroma_key(open_rgba(RAW_DIR / "ui_concept.png"))
    for spec in UI_SPECS:
        cropped = crop_relative(concept, spec)
        fit_to_canvas(cropped, spec.target_size, padding=2).save(UI_DIR / f"{spec.name}.png")


def process_path_variants() -> None:
    source = open_rgba(RAW_DIR / "path_variants.png")
    cell_width = source.width // 4
    names = ["path_straight", "path_corner", "path_t", "path_cross"]
    for index, name in enumerate(names):
        crop = source.crop((index * cell_width, 0, (index + 1) * cell_width, source.height))
        crop.resize((48, 48), Image.Resampling.LANCZOS).save(TILE_DIR / f"{name}.png")


def make_texture_variant(source: Path, target: Path, variant: str) -> None:
    image = Image.open(source).convert("RGBA")
    draw = ImageDraw.Draw(image)
    if variant == "gravel":
        image = ImageEnhance.Color(image).enhance(0.35)
        image = ImageEnhance.Brightness(image).enhance(0.88)
        colors = [(95, 91, 82, 255), (126, 121, 108, 255), (69, 70, 65, 255)]
        for index in range(34):
            x = (index * 17 + 5) % 48
            y = (index * 29 + 11) % 48
            draw.rectangle((x, y, x + 2, y + 1), fill=colors[index % len(colors)])
    elif variant == "rocky":
        image = ImageEnhance.Contrast(image).enhance(1.25)
        colors = [(82, 85, 81, 255), (119, 121, 112, 255)]
        for index in range(18):
            x = (index * 19 + 7) % 48
            y = (index * 13 + 9) % 48
            draw.polygon(
                [(x, y), (x + 5, y + 2), (x + 3, y + 6), (x - 1, y + 4)],
                fill=colors[index % 2],
            )
    elif variant == "flowers":
        colors = [(224, 78, 81, 255), (244, 196, 75, 255), (164, 99, 190, 255)]
        for index, color in enumerate(colors):
            x = (index * 13 + 8) % 42 + 3
            y = (index * 17 + 12) % 42 + 3
            draw.rectangle((x, y, x + 1, y + 1), fill=color)
            draw.point((x + 2, y), fill=color)
            draw.point((x, y + 2), fill=color)
    image.save(target)


def make_building_variant(
    source_name: str,
    target_name: str,
    tint: tuple[float, float, float],
    banner: tuple[int, int, int],
) -> None:
    source = Image.open(OBJECT_DIR / f"{source_name}.png").convert("RGBA")
    pixels = source.load()
    for y in range(source.height):
        for x in range(source.width):
            r, g, b, a = pixels[x, y]
            if a:
                pixels[x, y] = (
                    min(255, int(r * tint[0])),
                    min(255, int(g * tint[1])),
                    min(255, int(b * tint[2])),
                    a,
                )
    draw = ImageDraw.Draw(source)
    center = source.width // 2
    draw.rectangle((center - 18, 12, center + 18, 22), fill=(*banner, 255))
    draw.rectangle((center - 14, 16, center + 14, 18), fill=(246, 220, 142, 255))
    source.save(OBJECT_DIR / f"{target_name}.png")


def main() -> None:
    ensure_dirs()
    process_characters()
    process_tiles()
    process_objects()
    process_ui()
    print("processed generated assets")


if __name__ == "__main__":
    main()
