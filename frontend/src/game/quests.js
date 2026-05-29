import { TILE_SIZE } from "./constants.js";

const INTERACTION_RANGE = 72;

export function findInteraction(state) {
  if (!state.player) return null;
  const player = { x: state.player.x + 24, y: state.player.y + 24 };
  const candidates = [];

  for (const npc of state.npcs) {
    candidates.push({
      type: "npc",
      id: npc.id,
      label: `Parler à ${npc.name}`,
      x: npc.x + 24,
      y: npc.y + 24,
      npc,
    });
  }

  for (const resource of state.resources) {
    candidates.push({
      type: "resource",
      id: resource.id,
      label: actionLabel(resource.kind),
      x: resource.x + 24,
      y: resource.y + 24,
      resource,
    });
  }

  return candidates
    .map((candidate) => ({ ...candidate, distance: distance(player, candidate) }))
    .filter((candidate) => candidate.distance <= INTERACTION_RANGE)
    .sort((a, b) => a.distance - b.distance)[0] ?? null;
}

export function actionLabel(kind) {
  if (kind === "tree") return "Couper l'arbre";
  if (kind === "ore") return "Miner le filon";
  return "Miner la roche";
}

export function questTargetLabel(state) {
  const step = state.quest?.steps?.[state.quest.step_index];
  if (!step) return "";
  if (step.kind === "talk" && step.target_id) {
    const npc = state.npcs.find((item) => item.id === step.target_id);
    return npc ? `Objectif : ${npc.name} au bloc ${blockX(npc.x)}, ${blockY(npc.y)}` : "";
  }
  if (step.kind === "harvest") {
    const resource = nearestResource(state);
    return resource ? `Objectif : ressource au bloc ${blockX(resource.x)}, ${blockY(resource.y)}` : "";
  }
  if (step.kind === "sql") {
    const sage = state.npcs.find((item) => item.id === "sage-oracle");
    return sage ? `Objectif : Sage Oracle au bloc ${blockX(sage.x)}, ${blockY(sage.y)}` : "";
  }
  return "";
}

function nearestResource(state) {
  if (!state.player || state.resources.length === 0) return null;
  return [...state.resources].sort(
    (a, b) => distance(state.player, a) - distance(state.player, b),
  )[0];
}

function blockX(worldX) {
  return Math.floor(worldX / TILE_SIZE);
}

function blockY(worldY) {
  return Math.floor(worldY / TILE_SIZE);
}

function distance(a, b) {
  return Math.hypot(a.x - b.x, a.y - b.y);
}
