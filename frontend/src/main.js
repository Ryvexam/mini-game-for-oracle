import {
  answerSql,
  createSession,
  deposit,
  fetchHealth,
  fetchStats,
  fetchWorld,
  harvest,
  saveMove,
  talk,
} from "./game/api.js";
import { loadAssets } from "./game/assets.js";
import { CANVAS_HEIGHT, CANVAS_WIDTH } from "./game/constants.js";
import { applyActionResult, applyWorldState, createInitialState, currentChunk } from "./game/gameState.js";
import { createInput } from "./game/input.js";
import { formatCoordinates, reloadWorldMap, renderBigMap, renderMiniMap } from "./game/minimap.js";
import { updatePlayer } from "./game/player.js";
import { findInteraction, questTargetLabel } from "./game/quests.js";
import { clearChunkCache, render } from "./game/renderer.js";
import { connectPresence, disconnectPresence, sendChat, sendPresence } from "./game/websocket.js";

const canvas = document.querySelector("#game");
const ctx = canvas.getContext("2d");
const warning = document.querySelector("#oracle-warning");
const questTitle = document.querySelector("#quest-title");
const questText = document.querySelector("#quest-text");
const sqlBox = document.querySelector("#sql-box");
const progressList = document.querySelector("#progress-list");
const coords = document.querySelector("#coords");
const minimap = document.querySelector("#minimap");
const minimapCtx = minimap.getContext("2d");
const login = document.querySelector("#login");
const loginForm = document.querySelector("#login-form");
const pseudoInput = document.querySelector("#pseudo");
const menuButton = document.querySelector("#open-menu");
const mapButton = document.querySelector("#open-map");
const logoutButton = document.querySelector("#logout");
const mapOverlay = document.querySelector("#map-overlay");
const closeMapButton = document.querySelector("#close-map");
const umlOverlay = document.querySelector("#uml-overlay");
const closeUmlButton = document.querySelector("#close-uml");
const bigMap = document.querySelector("#big-map");
const bigMapCtx = bigMap.getContext("2d");

menuButton.addEventListener("click", () => {
  if (state?.player) toggleStats();
});

const MAP_VIEW_TILES = 400; // tiles visible across the big map
const MAP_PAN_STEP = 40;
const MAP_HALF = 1000; // world-map.png spans -1000..+1000

mapButton.addEventListener("click", () => openMap());

function clampCenter(value) {
  return Math.max(-MAP_HALF, Math.min(MAP_HALF, value));
}

function openMap() {
  if (!state?.player) return;
  state.mapOpen = true;
  state.mapView = MAP_VIEW_TILES;
  state.mapCenter = {
    x: clampCenter(Math.floor((state.player.x + 24) / TILE_SIZE)),
    y: clampCenter(Math.floor((state.player.y + 24) / TILE_SIZE)),
  };
}

function panMap(dx, dy) {
  if (!state?.mapCenter) return;
  state.mapCenter = {
    x: clampCenter(state.mapCenter.x + dx * MAP_PAN_STEP),
    y: clampCenter(state.mapCenter.y + dy * MAP_PAN_STEP),
  };
}

closeMapButton.addEventListener("click", () => {
  if (state) state.mapOpen = false;
});

function toggleUml() {
  umlOverlay.hidden = !umlOverlay.hidden;
}

closeUmlButton.addEventListener("click", () => {
  umlOverlay.hidden = true;
});

logoutButton.addEventListener("click", () => logout());

canvas.width = CANVAS_WIDTH;
canvas.height = CANVAS_HEIGHT;
ctx.imageSmoothingEnabled = false;
minimapCtx.imageSmoothingEnabled = false;
bigMapCtx.imageSmoothingEnabled = false;

const input = createInput();
const assets = await loadAssets();
let state = null;

try {
  await fetchHealth();
  warning.hidden = true;
} catch (error) {
  warning.hidden = false;
  warning.textContent = error.message;
}

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const pseudo = pseudoInput.value.trim();
  if (!pseudo) return;
  try {
    state = createInitialState({ pseudo, assets });
    const player = await createSession(pseudo, null);
    state.player = { ...player, direction: "down", frame: 0, animationMs: 0 };
    await refreshWorld({ preserveLocalPosition: false });
    connectPresence(state);
    login.hidden = true;
    logoutButton.hidden = false;
    warning.hidden = true;
  } catch (error) {
    warning.hidden = false;
    warning.textContent = error.message;
  }
});

function logout() {
  if (state) {
    disconnectPresence(state);
    state.mapOpen = false;
    state.statsOpen = false;
  }
  state = null;
  pseudoInput.value = "";
  login.hidden = false;
  logoutButton.hidden = true;
  mapOverlay.hidden = true;
}

async function refreshWorld(options = {}) {
  if (!state?.player) return;
  const chunk = currentChunk(state.player);
  const world = await fetchWorld(state.pseudo, chunk.x, chunk.y);
  applyWorldState(state, world, options);
  syncPanel();
}

async function handleAction() {
  if (!state?.nearbyInteraction) return;
  const interaction = state.nearbyInteraction;
  try {
    if (interaction.type === "resource") {
      state.player.action = "mining";
      state.player.actionMs = 1000;
    }
    let result;
    if (interaction.type === "npc") {
      result = await talk(state.pseudo, interaction.id);
    } else if (interaction.type === "chest") {
      result = await deposit(state.pseudo, interaction.id);
    } else {
      result = await harvest(state.pseudo, interaction.id);
    }
    applyActionResult(state, result);
    await refreshWorld();
  } catch (error) {
    state.message = { text: error.message, ttl: 2600 };
  }
}

async function handleSqlAnswer(index) {
  if (!state?.quest?.sql_challenge) return;
  try {
    const result = await answerSql(state.pseudo, state.quest.sql_challenge.id, index);
    applyActionResult(state, result);
    await refreshWorld();
  } catch (error) {
    state.message = { text: error.message, ttl: 2600 };
  }
}

function syncPanel() {
  if (!state?.player) return;
  questTitle.textContent = state.quest?.title ?? "Exploration";
  const step = state.quest?.steps?.[state.quest.step_index];
  const target = questTargetLabel(state);
  questText.textContent = [
    step?.text ?? "Explore le monde, récolte des ressources et parle aux PNJ.",
    target,
  ]
    .filter(Boolean)
    .join(" ");
  sqlBox.textContent = state.quest?.sql_challenge?.sql_code ?? "Aucune question SQL active.";
  progressList.innerHTML = "";
  coords.textContent = formatCoordinates(state.player);
  [
    `Joueur : ${state.player.pseudo}`,
    `Bois : ${state.player.wood}`,
    `Pierre : ${state.player.stone}`,
    `Minerai : ${state.player.ore}`,
  ].forEach((line) => {
    const node = document.createElement("div");
    node.className = "progress-item";
    node.textContent = line;
    progressList.append(node);
  });
}

async function toggleStats() {
  if (!state?.player) return;
  state.statsOpen = !state.statsOpen;
  if (state.statsOpen) {
    try {
      state.stats = await fetchStats(state.pseudo);
    } catch (error) {
      state.message = { text: error.message, ttl: 2600 };
    }
  }
}

window.addEventListener("keydown", (event) => {
  if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement) return;

  if (!umlOverlay.hidden) {
    if (event.key === "Escape" || event.key.toLowerCase() === "p") {
      event.preventDefault();
      umlOverlay.hidden = true;
    }
    return;
  }
  if (event.key.toLowerCase() === "p" && state?.chatInput == null) {
    event.preventDefault();
    toggleUml();
    return;
  }

  if (!state?.player) return;
  const key = event.key;

  // Chat capture mode swallows gameplay keys.
  if (state.chatInput != null) {
    event.preventDefault();
    if (key === "Enter") {
      sendChat(state, state.chatInput);
      state.chatInput = null;
    } else if (key === "Escape") {
      state.chatInput = null;
    } else if (key === "Backspace") {
      state.chatInput = state.chatInput.slice(0, -1);
    } else if (key.length === 1 && state.chatInput.length < 120) {
      state.chatInput += key;
    }
    return;
  }

  if (state.mapOpen) {
    event.preventDefault();
    const lower = key.toLowerCase();
    if (key === "Escape" || lower === "c") {
      state.mapOpen = false;
    } else if (key === "ArrowUp" || lower === "z" || lower === "w") {
      panMap(0, -1);
    } else if (key === "ArrowDown" || lower === "s") {
      panMap(0, 1);
    } else if (key === "ArrowLeft" || lower === "q" || lower === "a") {
      panMap(-1, 0);
    } else if (key === "ArrowRight" || lower === "d") {
      panMap(1, 0);
    }
    return;
  }
  if (key.toLowerCase() === "c") {
    event.preventDefault();
    openMap();
    return;
  }
  if (key === "Tab" || key.toLowerCase() === "m") {
    event.preventDefault();
    toggleStats();
    return;
  }
  if (state.statsOpen) {
    if (key === "Escape") {
      event.preventDefault();
      state.statsOpen = false;
    }
    return;
  }
  if (key === "Enter" || key.toLowerCase() === "t") {
    event.preventDefault();
    state.chatInput = "";
    return;
  }
  if (key.toLowerCase() === "e") handleAction();
  if (["1", "2", "3"].includes(key)) handleSqlAnswer(Number(key) - 1);
});

let lastTime = performance.now();
function tick(now) {
  const delta = Math.min(40, now - lastTime);
  lastTime = now;
  if (state?.duplicate) {
    const text = state.duplicate;
    logout();
    warning.hidden = false;
    warning.textContent = text;
  }
  if (state?.player && state.worldResetSeed && state.worldResetSeed !== state.appliedResetSeed) {
    state.appliedResetSeed = state.worldResetSeed;
    clearChunkCache();
    reloadWorldMap(state.worldResetSeed);
    refreshWorld({ preserveLocalPosition: false }).catch((error) => {
      state.oracleError = error.message;
    });
  }
  if (state?.player) {
    state.dayMs = (state.dayMs ?? 0) + delta;
    interpolateOthers(state, delta);
    mapOverlay.hidden = !state.mapOpen;
    if (state.mapOpen) renderBigMap(bigMapCtx, state);
    const inputLocked = state.chatInput != null || state.statsOpen || state.mapOpen;
    if (!inputLocked) updatePlayer(state, input, delta);
    state.nearbyInteraction = inputLocked ? null : findInteraction(state);
    state.syncMs += delta;
    state.moveSyncMs += delta;
    state.presenceSyncMs += delta;
    if (state.moveSyncMs > 300) {
      state.moveSyncMs = 0;
      syncPlayerPosition();
    }
    if (state.presenceSyncMs > 120) {
      state.presenceSyncMs = 0;
      sendPresence(state);
    }
    if (state.syncMs > 1800) {
      state.syncMs = 0;
      refreshWorld().catch((error) => {
        state.oracleError = error.message;
      });
    }
    syncPanel();
  }
  render(ctx, state ?? { oracleError: "Entre ton pseudo pour lancer la partie." }, assets);
  renderMiniMap(minimapCtx, state);
  requestAnimationFrame(tick);
}

requestAnimationFrame(tick);

function interpolateOthers(state, delta) {
  const factor = Math.min(1, delta / 110);
  for (const player of state.otherPlayers) {
    player.renderX = (player.renderX ?? player.x) + (player.x - (player.renderX ?? player.x)) * factor;
    player.renderY = (player.renderY ?? player.y) + (player.y - (player.renderY ?? player.y)) * factor;
  }
}

function syncPlayerPosition() {
  if (!state?.player || state.moveInFlight || !state.positionDirty) return;
  const x = Math.round(state.player.x);
  const y = Math.round(state.player.y);
  const last = state.lastSyncedPosition;
  if (last && Math.abs(last.x - x) < 2 && Math.abs(last.y - y) < 2) {
    state.positionDirty = false;
    return;
  }

  state.moveInFlight = true;
  saveMove(state.pseudo, x, y)
    .then(() => {
      state.lastSyncedPosition = { x, y };
      const currentX = Math.round(state.player.x);
      const currentY = Math.round(state.player.y);
      state.positionDirty = Math.abs(currentX - x) >= 2 || Math.abs(currentY - y) >= 2;
      state.oracleError = null;
    })
    .catch((error) => {
      state.oracleError = error.message;
    })
    .finally(() => {
      state.moveInFlight = false;
    });
}
