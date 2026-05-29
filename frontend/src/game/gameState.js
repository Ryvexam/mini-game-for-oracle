import { CHUNK_PIXELS } from "./constants.js";

export function createInitialState({ pseudo, assets }) {
  return {
    pseudo,
    assets,
    player: null,
    otherPlayers: [],
    chunks: [],
    resources: [],
    npcs: [],
    chests: [],
    quest: null,
    mapOpen: false,
    selectedSqlAnswer: 0,
    camera: { x: 0, y: 0 },
    nearbyInteraction: null,
    message: null,
    oracleError: null,
    syncMs: 0,
    moveSyncMs: 0,
    positionDirty: false,
    moveInFlight: false,
    lastSyncedPosition: null,
    presenceSocket: null,
    presenceSyncMs: 0,
    presenceReconnectMs: 800,
    presenceHeartbeat: null,
    connected: false,
    chatLog: [],
    chatInput: null,
    stats: null,
    statsOpen: false,
    dayMs: 0,
  };
}

export function applyWorldState(state, world, options = {}) {
  state.player = mergeServerPlayer(state.player, world.player, options);
  // Other players come live over WebSocket; only seed from REST before connecting.
  if (!state.connected && (state.otherPlayers?.length ?? 0) === 0) {
    state.otherPlayers = (world.players ?? []).map((player) => ({
      ...player,
      renderX: player.x,
      renderY: player.y,
    }));
  }
  state.chunks = world.chunks ?? [];
  state.resources = state.chunks.flatMap((chunk) => chunk.resources ?? []);
  state.npcs = state.chunks.flatMap((chunk) => chunk.npcs ?? []);
  state.chests = world.chests ?? [];
  state.quest = world.quest;
}

export function applyActionResult(state, result, options = {}) {
  state.player = mergeServerPlayer(state.player, result.player, {
    preserveLocalPosition: true,
    ...options,
  });
  state.quest = result.quest;
  state.message = { text: result.message, ttl: 2600 };
}

export function currentChunk(player) {
  return {
    x: Math.floor(player.x / CHUNK_PIXELS),
    y: Math.floor(player.y / CHUNK_PIXELS),
  };
}

function mergeServerPlayer(localPlayer, serverPlayer, options = {}) {
  const preserveLocalPosition = options.preserveLocalPosition ?? true;
  if (!localPlayer || !preserveLocalPosition) {
    return {
      ...serverPlayer,
      direction: localPlayer?.direction ?? "down",
      frame: localPlayer?.frame ?? 0,
      animationMs: localPlayer?.animationMs ?? 0,
      action: localPlayer?.action ?? null,
      actionMs: localPlayer?.actionMs ?? 0,
      moving: false,
    };
  }
  return {
    ...serverPlayer,
    x: localPlayer.x,
    y: localPlayer.y,
    direction: localPlayer.direction ?? "down",
    frame: localPlayer.frame ?? 0,
    animationMs: localPlayer.animationMs ?? 0,
    action: localPlayer.action ?? null,
    actionMs: localPlayer.actionMs ?? 0,
    moving: localPlayer.moving ?? false,
  };
}
