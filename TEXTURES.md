# Texture Generation Guide for Codex

This document is the complete brief for **Codex** to (re)generate every visual
asset of *Oracle Object Adventure*. The game already runs with placeholder art;
Codex's job is to produce higher-quality replacements at the **exact paths and
pixel sizes** listed below. The runtime loads assets by hard-coded path
(`frontend/src/game/assets.js`), so filenames and dimensions must not change.

## Global Style

- Top-down 2D, cohesive cozy-fantasy palette (warm greens, sandy paths, teal
  water, slate-grey mountains).
- Pixel-art friendly: crisp edges, no anti-aliased halos. Rendering uses
  `imageSmoothingEnabled = false`, so art should look intentional at 1:1.
- Transparent backgrounds (PNG with alpha) for everything except full tiles.
- Consistent top-left light source for shading across all assets.

## 1. Terrain Tiles — `assets/generated/tiles/`

Each tile is **48×48 px**, fully opaque, seamlessly tileable on all four edges.

| File | Biome / use | Notes |
|------|-------------|-------|
| `grass.png` | Plains (`g`) | Base ground, most common |
| `flower_grass.png` | Lush forest floor (`f`) | Grass with sparse flowers |
| `dirt.png` | Roads + beaches (`d`, `p`) | Packed earth path |
| `gravel.png` | River banks / scree (`v`) | Loose small stones |
| `rocky.png` | Rocky highlands (`r`) | Cracked stony ground |
| `stone.png` | Mountains (`s`) | Hard grey mountain rock |
| `water.png` | Rivers (`w`) | Animated-looking ripples, teal |
| `path_straight.png`, `path_corner.png`, `path_t.png`, `path_cross.png`, `path.png` | Optional road decorations | Reserved for future auto-tiling |

The single-letter codes in parentheses are the server tile codes
(`backend/db/oracle_object_repository.py: tile_code_at`). The code→texture map
lives in `frontend/src/game/renderer.js: TILE_BY_CODE`.

## 2. World Objects — `assets/generated/objects/`

Transparent PNGs, drawn anchored at their top-left.

| File | Subject | Target size | Rendered size |
|------|---------|-------------|---------------|
| `tree.png` | Harvestable tree | 96×96 | 62×58 |
| `rock.png` | Rock + ore node (shared) | 80×80 | 62×58 |
| `type_forge.png` | Village forge building | 224×196 | 112×98 |
| `object_village.png` | Village hall | 224×196 | 112×98 |
| `method_dojo.png` | Village dojo | 224×196 | 112×98 |
| `poly_arena.png`, `ref_bridge.png`, `collection_chest.png`, `final_gate.png` | Future landmarks | 224×196 | reserved |

Provide art at the larger "target size" (2× the rendered size) for crispness.
`rock.png` is reused for both `rock` and `ore` resource kinds — keep it readable
as a generic mineable boulder.

## 3. Character Sprite Sheets — `assets/generated/sprites/*_sheet.png`

Each sheet is **192×192 px** = a **4×4 grid of 48×48 frames**.

- **Rows = facing direction**, in this exact order:
  `row 0 = down, row 1 = left, row 2 = right, row 3 = up`
  (see `frontend/src/game/constants.js: DIRECTIONS`).
- **Columns = walk animation frames** (4 frames per direction).
- Frame 0 of each row is the idle/standing pose.

Required sheets (one per skin id):

```
player_sheet.png          human_sheet.png         monkey_sheet.png
lynx_sheet.png            oracle_sage_sheet.png   collection_keeper_sheet.png
living_being_sheet.png    ref_spirit_sheet.png    final_guardian_sheet.png
```

Skins actually selectable in game: `player`, `human`, `monkey`, `lynx`,
`oracle_sage`, `collection_keeper` (`SKINS` in the repository module). NPC roles
map to sprites in `renderer.js: drawNpcs` — `oracle_sage` (sage), `monkey`
(merchant), `lynx` (miner).

## 4. Mining Animations — `assets/generated/sprites/*_mining.gif`

Animated GIFs, **96×96 px**, looping, transparent background. One per skin, named
`<skin>_mining.gif` (e.g. `player_mining.gif`, `oracle_sage_mining.gif`). Shown
while a character harvests (`renderer.js: drawMiningAnimation`). Match each GIF's
character design to its corresponding sprite sheet.

There are also idle preview GIFs (`<skin>.gif`) used for documentation; lower
priority.

## 5. UI — `assets/generated/ui/`

| File | Use | Size |
|------|-----|------|
| `dialog_box.png` | Dialogue panel frame | 480×160 (9-slice friendly) |
| `oracle_icon.png` | Brand / loading icon | 96×96 |
| `interaction_prompt.png` | "Press E" badge | 96×48 |

## Pipeline & Validation

Regeneration scripts live in `scripts/` and are wired in `AGENTS.md`:

```bash
python scripts/generate_concept_assets.py   # raw concept sheets
python scripts/process_assets.py            # final PNGs
python scripts/build_hatch_pet_mascot.py    # validated pet atlases
python scripts/generate_gifs.py             # GIF previews
```

After regenerating, verify in-browser: `uvicorn backend.main:app --reload`,
open <http://127.0.0.1:8000>, and confirm tiles align, sprites face the right
way per direction row, and mining GIFs sit over the character.

## Checklist for Codex

- [ ] 7 active terrain tiles (grass, flower_grass, dirt, gravel, rocky, stone, water) at 48×48, seamless.
- [ ] tree + rock objects with transparency.
- [ ] 6 playable sprite sheets, 4×4 grid, direction rows in `down,left,right,up` order.
- [ ] matching `*_mining.gif` for each playable skin at 96×96.
- [ ] 3 village building objects.
- [ ] UI frames.
