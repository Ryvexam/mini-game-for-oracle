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

function distance(a, b) {
  return Math.hypot(a.x - b.x, a.y - b.y);
}
