const IMAGE_ASSETS = {
  sprites: {
    player: "/assets/generated/sprites/player_sheet.png",
    living_being: "/assets/generated/sprites/living_being_sheet.png",
    human: "/assets/generated/sprites/human_sheet.png",
    monkey: "/assets/generated/sprites/monkey_sheet.png",
    lynx: "/assets/generated/sprites/lynx_sheet.png",
    oracle_sage: "/assets/generated/sprites/oracle_sage_sheet.png",
    ref_spirit: "/assets/generated/sprites/ref_spirit_sheet.png",
    collection_keeper: "/assets/generated/sprites/collection_keeper_sheet.png",
    final_guardian: "/assets/generated/sprites/final_guardian_sheet.png",
  },
  tiles: {
    grass: "/assets/generated/tiles/grass.png",
    dirt: "/assets/generated/tiles/dirt.png",
    stone: "/assets/generated/tiles/stone.png",
    water: "/assets/generated/tiles/water.png",
    path: "/assets/generated/tiles/path.png",
    path_straight: "/assets/generated/tiles/path_straight.png",
    path_corner: "/assets/generated/tiles/path_corner.png",
    path_t: "/assets/generated/tiles/path_t.png",
    path_cross: "/assets/generated/tiles/path_cross.png",
    gravel: "/assets/generated/tiles/gravel.png",
    rocky: "/assets/generated/tiles/rocky.png",
    flower_grass: "/assets/generated/tiles/flower_grass.png",
  },
  objects: {
    tree: "/assets/generated/objects/tree.png",
    rock: "/assets/generated/objects/rock.png",
    ore: "/assets/generated/objects/rock.png",
    type_forge: "/assets/generated/objects/type_forge.png",
    method_dojo: "/assets/generated/objects/method_dojo.png",
    object_village: "/assets/generated/objects/object_village.png",
    poly_arena: "/assets/generated/objects/poly_arena.png",
    ref_bridge: "/assets/generated/objects/ref_bridge.png",
    collection_chest: "/assets/generated/objects/collection_chest.png",
    final_gate: "/assets/generated/objects/final_gate.png",
  },
  ui: {
    dialog_box: "/assets/generated/ui/dialog_box.png",
    oracle_icon: "/assets/generated/ui/oracle_icon.png",
    interaction_prompt: "/assets/generated/ui/interaction_prompt.png",
  },
};

function loadImage(src) {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = () => reject(new Error(`Failed to load ${src}`));
    image.src = src;
  });
}

export async function loadAssets() {
  const result = {};
  for (const [group, entries] of Object.entries(IMAGE_ASSETS)) {
    result[group] = {};
    for (const [name, src] of Object.entries(entries)) {
      result[group][name] = await loadImage(src);
    }
  }
  return result;
}
