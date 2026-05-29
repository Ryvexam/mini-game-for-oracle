from __future__ import annotations

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "assets" / "generated" / "raw"
ATLAS_DIR = RAW_DIR / "pet_atlases"
SPRITE_DIR = ROOT / "assets" / "generated" / "sprites"

PETS = [
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

COLUMNS = 6
ROWS = 8
ATLAS_CELL = 128
GIF_SIZE = 96
MINING_ROWS = range(3, 6)


def main() -> None:
    ATLAS_DIR.mkdir(parents=True, exist_ok=True)
    SPRITE_DIR.mkdir(parents=True, exist_ok=True)
    for pet_id in PETS:
        sheet_path = RAW_DIR / f"{pet_id}_mining_imagegen_sheet.png"
        if not sheet_path.exists():
            raise FileNotFoundError(f"missing imagegen mining sheet: {sheet_path}")
        frames = extract_frames(sheet_path)
        atlas = build_atlas(frames)
        atlas.save(ATLAS_DIR / f"{pet_id}_mining_grid.png")
        write_gif(pet_id, [frame for row in MINING_ROWS for frame in frames[row]])
        print(f"wrote imagegen-based mining assets for {pet_id}")


def extract_frames(path: Path) -> list[list[Image.Image]]:
    source = remove_magenta(Image.open(path).convert("RGBA"))
    row_bands = detect_bands(source, axis="y", expected=ROWS, threshold=20, min_size=16)
    rows: list[list[Image.Image]] = []
    for top, bottom in row_bands:
        row_image = source.crop((0, top, source.width, bottom))
        column_bands = detect_bands(row_image, axis="x", expected=COLUMNS, threshold=5, min_size=8)
        frames = []
        for left, right in column_bands:
            frame = row_image.crop((left, 0, right, row_image.height))
            frames.append(normalize_frame(frame, ATLAS_CELL))
        rows.append(frames)
    return rows


def detect_bands(
    image: Image.Image, axis: str, expected: int, threshold: int, min_size: int
) -> list[tuple[int, int]]:
    length = image.height if axis == "y" else image.width
    cross_length = image.width if axis == "y" else image.height
    alpha = image.getchannel("A")
    counts = []
    for primary in range(length):
        count = 0
        for secondary in range(cross_length):
            x, y = (secondary, primary) if axis == "y" else (primary, secondary)
            if alpha.getpixel((x, y)) > 0:
                count += 1
        counts.append(count)

    scored_bands: list[tuple[int, int, int]] = []
    start = None
    for index, count in enumerate(counts):
        if count > threshold and start is None:
            start = index
        at_end = index == len(counts) - 1
        if start is not None and (count <= threshold or at_end):
            end = index if count <= threshold else index + 1
            if end - start >= min_size:
                scored_bands.append((start, end, sum(counts[start:end])))
            start = None

    if len(scored_bands) > expected:
        scored_bands = sorted(scored_bands, key=lambda band: band[2], reverse=True)[:expected]
        scored_bands = sorted(scored_bands, key=lambda band: band[0])

    bands = [(start, end) for start, end, _score in scored_bands]
    if len(bands) != expected:
        raise ValueError(f"expected {expected} {axis}-bands, found {len(bands)} for {image.size}")
    return bands


def remove_magenta(image: Image.Image) -> Image.Image:
    pixels = image.load()
    for y in range(image.height):
        for x in range(image.width):
            red, green, blue, alpha = pixels[x, y]
            if red > 170 and blue > 130 and green < 90:
                pixels[x, y] = (0, 0, 0, 0)
            elif alpha > 0:
                pixels[x, y] = (red, green, blue, 255)
    return image


def normalize_frame(frame: Image.Image, size: int) -> Image.Image:
    bbox = frame.getbbox()
    if bbox:
        frame = frame.crop(bbox)
    frame.thumbnail((size - 16, size - 16), Image.Resampling.NEAREST)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    canvas.alpha_composite(frame, ((size - frame.width) // 2, (size - frame.height) // 2))
    return canvas


def build_atlas(rows: list[list[Image.Image]]) -> Image.Image:
    atlas = Image.new("RGBA", (COLUMNS * ATLAS_CELL, ROWS * ATLAS_CELL), (0, 0, 0, 0))
    for row_index, row in enumerate(rows):
        for column, frame in enumerate(row):
            atlas.alpha_composite(frame, (column * ATLAS_CELL, row_index * ATLAS_CELL))
    return atlas


def write_gif(pet_id: str, frames: list[Image.Image]) -> None:
    gif_frames = [frame.resize((GIF_SIZE, GIF_SIZE), Image.Resampling.NEAREST) for frame in frames]
    gif_frames[0].save(
        SPRITE_DIR / f"{pet_id}_mining.gif",
        save_all=True,
        append_images=gif_frames[1:],
        duration=90,
        loop=0,
        disposal=2,
    )


if __name__ == "__main__":
    main()
