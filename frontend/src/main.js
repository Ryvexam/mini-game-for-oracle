import {
  answerSql,
  createSession,
  fetchHealth,
  fetchWorld,
  harvest,
  saveMove,
  talk,
} from "./game/api.js";
import { loadAssets } from "./game/assets.js";
import { CANVAS_HEIGHT, CANVAS_WIDTH } from "./game/constants.js";
import { applyActionResult, applyWorldState, createInitialState, currentChunk } from "./game/gameState.js";
import { createInput } from "./game/input.js";
import { formatCoordinates, renderMiniMap } from "./game/minimap.js";
import { updatePlayer } from "./game/player.js";
import { findInteraction, questTargetLabel } from "./game/quests.js";
import { render } from "./game/renderer.js";
import { connectPresence, sendPresence } from "./game/websocket.js";

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

canvas.width = CANVAS_WIDTH;
canvas.height = CANVAS_HEIGHT;
ctx.imageSmoothingEnabled = false;
minimapCtx.imageSmoothingEnabled = false;

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
  } catch (error) {
    warning.hidden = false;
    warning.textContent = error.message;
  }
});

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
      state.player.actionMs = 1200;
    }
    const result =
      interaction.type === "npc"
        ? await talk(state.pseudo, interaction.id)
        : await harvest(state.pseudo, interaction.id);
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

window.addEventListener("keydown", (event) => {
  if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement) return;
  if (event.key.toLowerCase() === "e") handleAction();
  if (["1", "2", "3"].includes(event.key)) handleSqlAnswer(Number(event.key) - 1);
});

let lastTime = performance.now();
function tick(now) {
  const delta = Math.min(40, now - lastTime);
  lastTime = now;
  if (state?.player) {
    updatePlayer(state, input, delta);
    state.nearbyInteraction = findInteraction(state);
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
