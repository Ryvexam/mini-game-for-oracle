from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "assets" / "generated" / "raw" / "pet_atlases"
SPRITE_DIR = ROOT / "assets" / "generated" / "sprites"

COLUMNS = 6
ROWS = 8
CELL = 128
GIF_SIZE = 96
PETS = {
    "player": {"fur": "#c99552", "inner": "#f1cf91", "body": "#0f766e", "tail": "#7b5427"},
    "living_being": {"fur": "#89b96f", "inner": "#cfe6a4", "body": "#416e43", "tail": "#527d3d"},
    "human": {"fur": "#d6a56b", "inner": "#f3d5a6", "body": "#365f91", "tail": "#7b5427"},
    "monkey": {"fur": "#9b6a3c", "inner": "#e0b275", "body": "#8c4b33", "tail": "#5d341d"},
    "lynx": {"fur": "#d19a4a", "inner": "#f4d39b", "body": "#704f31", "tail": "#3f3328"},
    "oracle_sage": {"fur": "#c8b6ff", "inner": "#f0e8ff", "body": "#6d4c9f", "tail": "#59437f"},
    "ref_spirit": {"fur": "#73d2de", "inner": "#d8fbff", "body": "#237b8a", "tail": "#1f7f94"},
    "collection_keeper": {
        "fur": "#f1c453",
        "inner": "#ffe6a1",
        "body": "#8a5f16",
        "tail": "#6f4d18",
    },
    "final_guardian": {"fur": "#b0b7c3", "inner": "#edf0f5", "body": "#7d2f2b", "tail": "#424852"},
}


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    SPRITE_DIR.mkdir(parents=True, exist_ok=True)

    for pet_id, palette in PETS.items():
        atlas = build_atlas(palette)
        atlas_path = RAW_DIR / f"{pet_id}_mining_grid.png"
        atlas.save(atlas_path)
        if pet_id == "player":
            atlas.save(RAW_DIR / "player_mining_grid.png")
        write_mining_gif(pet_id, atlas)
        print(f"wrote {atlas_path.relative_to(ROOT)}")
        print(f"wrote assets/generated/sprites/{pet_id}_mining.gif")


def build_atlas(palette: dict[str, str]) -> Image.Image:
    atlas = Image.new("RGBA", (COLUMNS * CELL, ROWS * CELL), (0, 0, 0, 0))
    for row in range(ROWS):
        for column in range(COLUMNS):
            frame = Image.new("RGBA", (CELL, CELL), (0, 0, 0, 0))
            draw_character(frame, row, column, palette)
            atlas.alpha_composite(frame, (column * CELL, row * CELL))
    return atlas


def write_mining_gif(pet_id: str, atlas: Image.Image) -> None:
    mining_frames = [
        atlas.crop((column * CELL, 5 * CELL, (column + 1) * CELL, 6 * CELL)).resize(
            (GIF_SIZE, GIF_SIZE),
            Image.Resampling.NEAREST,
        )
        for column in range(COLUMNS)
    ]
    mining_frames[0].save(
        SPRITE_DIR / f"{pet_id}_mining.gif",
        save_all=True,
        append_images=mining_frames[1:],
        duration=[160, 160, 150, 210, 170, 180],
        loop=0,
        disposal=2,
    )


def draw_character(frame: Image.Image, row: int, column: int, palette: dict[str, str]) -> None:
    draw = ImageDraw.Draw(frame)
    direction = direction_for_row(row)
    mining = row in {5, 6, 7}
    walk_shift = [0, -2, 0, 2, 0, -1][column] if row in {1, 2, 3, 4} else 0
    swing = mining_swing(column) if mining else 0

    body_x = 64
    body_y = 70 + walk_shift
    if direction == "left":
        body_x = 58
    elif direction == "right":
        body_x = 70

    draw_shadow(draw, body_x, body_y)
    draw_tail(draw, body_x, body_y, direction, mining, swing, palette)
    draw_body(draw, body_x, body_y, palette)
    draw_head(draw, body_x, body_y, direction, palette)
    draw_arms(draw, body_x, body_y, direction, mining, swing, palette)
    draw_legs(draw, body_x, body_y, column, row, palette)
    draw_pickaxe(draw, body_x, body_y, direction, mining, swing)
    if mining and column == 3:
        draw_impact(draw, body_x, body_y, direction)


def direction_for_row(row: int) -> str:
    return {
        0: "down",
        1: "down",
        2: "left",
        3: "right",
        4: "up",
        5: "down",
        6: "left",
        7: "right",
    }[row]


def mining_swing(column: int) -> int:
    return [-38, -24, -8, 24, 40, 10][column]


def draw_shadow(draw: ImageDraw.ImageDraw, x: int, y: int) -> None:
    draw.ellipse((x - 28, y + 27, x + 28, y + 39), fill=(27, 34, 31, 76))


def draw_body(draw: ImageDraw.ImageDraw, x: int, y: int, palette: dict[str, str]) -> None:
    draw.rounded_rectangle(
        (x - 19, y - 18, x + 19, y + 24),
        radius=8,
        fill=palette["body"],
        outline="#17221f",
        width=3,
    )
    draw.rectangle((x - 18, y + 4, x + 18, y + 11), fill="#7b5427")
    draw.rectangle((x - 5, y + 3, x + 5, y + 13), outline="#f6dfac", width=2)
    draw.polygon([(x - 17, y - 18), (x + 17, y - 18), (x, y - 1)], fill="#154f4c")


def draw_head(
    draw: ImageDraw.ImageDraw, x: int, y: int, direction: str, palette: dict[str, str]
) -> None:
    head_y = y - 39
    draw.ellipse(
        (x - 22, head_y - 18, x + 22, head_y + 22),
        fill=palette["fur"],
        outline="#17221f",
        width=3,
    )
    draw.polygon(
        [(x - 17, head_y - 10), (x - 10, head_y - 34), (x - 3, head_y - 11)],
        fill=palette["fur"],
        outline="#17221f",
    )
    draw.polygon(
        [(x + 17, head_y - 10), (x + 10, head_y - 34), (x + 3, head_y - 11)],
        fill=palette["fur"],
        outline="#17221f",
    )
    draw.polygon(
        [(x - 11, head_y - 14), (x - 10, head_y - 25), (x - 6, head_y - 13)],
        fill=palette["inner"],
    )
    draw.polygon(
        [(x + 11, head_y - 14), (x + 10, head_y - 25), (x + 6, head_y - 13)],
        fill=palette["inner"],
    )
    if direction == "up":
        draw.arc((x - 18, head_y - 3, x + 18, head_y + 18), 190, 350, fill="#7b5427", width=3)
        return
    eye_offset = -4 if direction == "left" else 4 if direction == "right" else 0
    draw.ellipse((x - 11 + eye_offset, head_y - 2, x - 5 + eye_offset, head_y + 4), fill="#0a4f46")
    draw.ellipse((x + 5 + eye_offset, head_y - 2, x + 11 + eye_offset, head_y + 4), fill="#0a4f46")
    draw.polygon(
        [(x - 2 + eye_offset, head_y + 7), (x + 2 + eye_offset, head_y + 7), (x, head_y + 11)],
        fill="#5d341d",
    )
    draw.arc(
        (x - 8 + eye_offset, head_y + 8, x + 8 + eye_offset, head_y + 18),
        20,
        160,
        fill="#17221f",
        width=2,
    )


def draw_arms(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    direction: str,
    mining: bool,
    swing: int,
    palette: dict[str, str],
) -> None:
    if not mining:
        draw.ellipse(
            (x - 31, y - 11, x - 17, y + 8), fill=palette["fur"], outline="#17221f", width=2
        )
        draw.ellipse(
            (x + 17, y - 11, x + 31, y + 8), fill=palette["fur"], outline="#17221f", width=2
        )
        return
    offset = swing // 5
    if direction == "left":
        draw.line((x - 17, y - 7, x - 34, y + offset), fill=palette["fur"], width=8)
    elif direction == "right":
        draw.line((x + 17, y - 7, x + 34, y + offset), fill=palette["fur"], width=8)
    else:
        draw.line(
            (x - 15, y - 8, x - 25 + offset, y - 22 + swing // 3),
            fill=palette["fur"],
            width=8,
        )
        draw.line(
            (x + 15, y - 8, x + 25 + offset, y - 22 + swing // 3),
            fill=palette["fur"],
            width=8,
        )


def draw_legs(
    draw: ImageDraw.ImageDraw, x: int, y: int, column: int, row: int, palette: dict[str, str]
) -> None:
    spread = 4 if column % 2 else -2
    if row in {0, 5, 6, 7}:
        spread = 0
    draw.ellipse(
        (x - 16 - spread, y + 19, x - 3 - spread, y + 35),
        fill=palette["fur"],
        outline="#17221f",
        width=2,
    )
    draw.ellipse(
        (x + 3 + spread, y + 19, x + 16 + spread, y + 35),
        fill=palette["fur"],
        outline="#17221f",
        width=2,
    )


def draw_tail(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    direction: str,
    mining: bool,
    swing: int,
    palette: dict[str, str],
) -> None:
    tail_y = y + (swing // 12 if mining else 0)
    if direction == "left":
        draw.arc(
            (x + 12, tail_y - 7, x + 46, tail_y + 33),
            90,
            245,
            fill=palette["tail"],
            width=7,
        )
    else:
        draw.arc(
            (x - 46, tail_y - 7, x - 12, tail_y + 33),
            -65,
            90,
            fill=palette["tail"],
            width=7,
        )


def draw_pickaxe(
    draw: ImageDraw.ImageDraw, x: int, y: int, direction: str, mining: bool, swing: int
) -> None:
    if direction == "left":
        base = (x - 33, y - 7)
        tip = (x - 49, y + 16 + swing // 5)
    elif direction == "right":
        base = (x + 33, y - 7)
        tip = (x + 49, y + 16 + swing // 5)
    else:
        base = (x + swing // 4, y - 42 + swing)
        tip = (x + swing // 6, y - 7 + max(swing, 0))
    if not mining:
        base = (x + 24, y - 45)
        tip = (x + 23, y + 22)

    draw.line((base[0], base[1], tip[0], tip[1]), fill="#6b4725", width=5)
    head_x, head_y = base
    draw.arc(
        (head_x - 20, head_y - 12, head_x + 20, head_y + 12), 190, 350, fill="#c9d0d2", width=6
    )
    draw.line((head_x - 14, head_y, head_x + 14, head_y), fill="#7f8c8d", width=3)


def draw_impact(draw: ImageDraw.ImageDraw, x: int, y: int, direction: str) -> None:
    impact_x = x if direction == "down" else x - 39 if direction == "left" else x + 39
    impact_y = y + 38
    draw.polygon(
        [(impact_x, impact_y - 15), (impact_x + 5, impact_y - 3), (impact_x - 3, impact_y)],
        fill="#ffd166",
    )
    draw.line((impact_x - 12, impact_y, impact_x + 12, impact_y + 4), fill="#6f6f66", width=4)
    draw.line((impact_x - 6, impact_y - 8, impact_x - 15, impact_y - 17), fill="#ffd166", width=2)
    draw.line((impact_x + 7, impact_y - 9, impact_x + 18, impact_y - 18), fill="#ffd166", width=2)


if __name__ == "__main__":
    main()
