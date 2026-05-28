export function createInitialState({ pseudo, assets }) {
  return {
    pseudo,
    assets,
    player: null,
    otherPlayers: [],
    chunks: [],
    resources: [],
    npcs: [],
    quest: null,
    selectedSqlAnswer: 0,
    camera: { x: 0, y: 0 },
    nearbyInteraction: null,
    message: null,
    oracleError: null,
    syncMs: 0,
    moveSyncMs: 0,
  };
}

export function applyWorldState(state, world) {
  state.player = world.player;
  state.otherPlayers = world.players ?? [];
  state.chunks = world.chunks ?? [];
  state.resources = state.chunks.flatMap((chunk) => chunk.resources ?? []);
  state.npcs = state.chunks.flatMap((chunk) => chunk.npcs ?? []);
  state.quest = world.quest;
}

export function applyActionResult(state, result) {
  state.player = result.player;
  state.quest = result.quest;
  state.message = { text: result.message, ttl: 2600 };
}

export function currentChunk(player) {
  return {
    x: Math.floor(player.x / 768),
    y: Math.floor(player.y / 768),
  };
}
