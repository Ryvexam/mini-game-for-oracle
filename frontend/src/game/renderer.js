import {
  CANVAS_HEIGHT,
  CANVAS_WIDTH,
  CHUNK_PIXELS,
  DIRECTIONS,
  FRAME_SIZE,
  TILE_SIZE,
} from "./constants.js";
import { MINING_DURATION_MS, MINING_FRAMES } from "./assets.js";
import { questTargetLabel } from "./quests.js";

const TILE_BY_CODE = {
  g: "grass",
  p: "dirt",
  w: "water",
  r: "rocky",
  f: "flower_grass",
  v: "gravel",
  d: "dirt",
  s: "stone",
};

export function render(ctx, state, assets) {
  ctx.clearRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);
  if (!state.player) {
    drawBlockingMessage(ctx, state.oracleError ?? "Connexion à Oracle en cours...");
    return;
  }

  updateCamera(state);
  drawChunks(ctx, state, assets);
  drawVillage(ctx, state, assets);
  drawResources(ctx, state, assets);
  drawChests(ctx, state, assets);
  drawNpcs(ctx, state, assets);
  drawOtherPlayers(ctx, state, assets);
  drawPlayer(ctx, state, assets);
  drawChatBubbles(ctx, state);
  drawDayNight(ctx, state);
  drawInteractionPrompt(ctx, state);
  drawHud(ctx, state);
  drawQuestPanel(ctx, state);
  drawChat(ctx, state);
  drawConnection(ctx, state);
  drawMessage(ctx, state);
  drawStatsOverlay(ctx, state);
}

function drawStatsOverlay(ctx, state) {
  if (!state.statsOpen) return;
  ctx.fillStyle = "rgba(12, 18, 16, 0.82)";
  ctx.fillRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);
  drawPanel(ctx, 140, 70, CANVAS_WIDTH - 280, CANVAS_HEIGHT - 150, "#fff8e8");
  drawCentered(ctx, "Statistiques Oracle", CANVAS_WIDTH / 2, 116, "#7d2f2b", 24);

  const stats = state.stats;
  drawControlsHelp(ctx);

  if (!stats) {
    drawCentered(ctx, "Chargement depuis Oracle…", CANVAS_WIDTH / 2, 180, "#17221f", 16);
    return;
  }

  const p = stats.player;
  let y = 160;
  if (p) {
    const lines = [
      `Rang : #${p.rank_position}`,
      `Bois récolté : ${p.wood_gathered}`,
      `Pierre récoltée : ${p.stone_gathered}`,
      `Minerai récolté : ${p.ore_gathered}`,
      `Récoltes totales : ${p.harvest_actions}`,
      `Distance parcourue : ${p.distance_moved} blocs`,
      `SQL : ${p.sql_correct}/${p.sql_attempts} correctes`,
    ];
    lines.forEach((line, index) => drawText(ctx, line, 180, y + index * 24, "#17221f", 15));
  }

  let by = 160;
  drawText(ctx, "Classement (récoltes)", CANVAS_WIDTH / 2 + 30, by, "#7d2f2b", 16);
  by += 26;
  stats.leaderboard.slice(0, 8).forEach((entry) => {
    const marker = entry.pseudo === state.pseudo ? "▸ " : "";
    drawText(
      ctx,
      `#${entry.rank_position}  ${marker}${entry.pseudo} — ${entry.total_gathered} (minerai ${entry.ore_gathered})`,
      CANVAS_WIDTH / 2 + 30,
      by,
      "#17221f",
      14,
    );
    by += 22;
  });
}

function drawControlsHelp(ctx) {
  const baseY = 356;
  drawText(ctx, "Commandes", 180, baseY, "#7d2f2b", 16);
  const controls = [
    "ZQSD / Flèches — se déplacer",
    "E — récolter / parler / déposer au coffre",
    "Entrée ou T — chat multijoueur",
    "1 / 2 / 3 — répondre au défi SQL",
    "C — ouvrir la grande carte",
    "Tab ou M — ouvrir / fermer ce menu",
    "Échap — fermer",
  ];
  controls.forEach((line, index) => drawText(ctx, line, 180, baseY + 24 + index * 20, "#17221f", 14));
  drawCentered(ctx, "Tab / M / Échap pour fermer", CANVAS_WIDTH / 2, CANVAS_HEIGHT - 108, "#5a4a3a", 13);
}

function drawDayNight(ctx, state) {
  // Full cycle every 4 minutes; darkness peaks at midnight, clear at noon.
  const phase = ((state.dayMs ?? 0) % 240000) / 240000;
  const darkness = (1 - Math.cos(phase * Math.PI * 2)) / 2;
  if (darkness <= 0.02) return;
  ctx.fillStyle = `rgba(12, 18, 38, ${darkness * 0.6})`;
  ctx.fillRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);
}

function drawChat(ctx, state) {
  const log = (state.chatLog ?? []).slice(-6);
  const typing = state.chatInput != null;
  if (log.length === 0 && !typing) return;
  const baseY = CANVAS_HEIGHT - (typing ? 118 : 90);
  log.forEach((entry, index) => {
    const y = baseY + index * 16;
    const text = entry.system ? entry.text : `${entry.pseudo}: ${entry.text}`;
    drawText(ctx, text, 20, y, entry.system ? "#9ad0c0" : "#fff8e8", 13);
  });
  if (typing) {
    drawPanel(ctx, 16, CANVAS_HEIGHT - 36, 420, 26, "rgba(23, 34, 31, 0.92)");
    drawText(ctx, `Dis : ${state.chatInput}_`, 26, CANVAS_HEIGHT - 18, "#fff8e8", 13);
  }
}

function drawConnection(ctx, state) {
  const online = state.connected;
  drawPanel(ctx, CANVAS_WIDTH - 132, CANVAS_HEIGHT - 36, 116, 24, "rgba(23, 34, 31, 0.9)");
  ctx.fillStyle = online ? "#6fd08c" : "#f0a14f";
  ctx.beginPath();
  ctx.arc(CANVAS_WIDTH - 118, CANVAS_HEIGHT - 24, 5, 0, Math.PI * 2);
  ctx.fill();
  drawText(ctx, online ? "En ligne" : "Reconnexion…", CANVAS_WIDTH - 106, CANVAS_HEIGHT - 19, "#fff8e8", 12);
}

function updateCamera(state) {
  state.camera.x = state.player.x + FRAME_SIZE / 2 - CANVAS_WIDTH / 2;
  state.camera.y = state.player.y + FRAME_SIZE / 2 - CANVAS_HEIGHT / 2;
}

// Each chunk's tiles are static, so rasterize them once to an offscreen canvas
// and blit a single image per chunk thereafter instead of 64 drawImage/frame.
const chunkCanvasCache = new Map();

export function clearChunkCache() {
  chunkCanvasCache.clear();
}

function getChunkCanvas(chunk, assets) {
  // Chunk tiles are deterministic per coordinate and never change, so a coord
  // key is enough — no rebuild even though each poll sends fresh tile arrays.
  const key = `${chunk.chunk_x},${chunk.chunk_y}`;
  const cached = chunkCanvasCache.get(key);
  if (cached) return cached.canvas;

  const canvas = document.createElement("canvas");
  canvas.width = CHUNK_PIXELS;
  canvas.height = CHUNK_PIXELS;
  const cctx = canvas.getContext("2d");
  cctx.clearRect(0, 0, CHUNK_PIXELS, CHUNK_PIXELS);
  chunk.tiles.forEach((row, tileY) => {
    for (let tileX = 0; tileX < row.length; tileX += 1) {
      const name = TILE_BY_CODE[row[tileX]] ?? "grass";
      cctx.drawImage(assets.tiles[name], tileX * TILE_SIZE, tileY * TILE_SIZE, TILE_SIZE, TILE_SIZE);
    }
  });

  chunkCanvasCache.set(key, { canvas });
  if (chunkCanvasCache.size > 256) {
    chunkCanvasCache.delete(chunkCanvasCache.keys().next().value);
  }
  return canvas;
}

function drawChunks(ctx, state, assets) {
  for (const chunk of state.chunks) {
    const x = chunk.chunk_x * CHUNK_PIXELS - state.camera.x;
    const y = chunk.chunk_y * CHUNK_PIXELS - state.camera.y;
    if (x <= -CHUNK_PIXELS || y <= -CHUNK_PIXELS || x >= CANVAS_WIDTH || y >= CANVAS_HEIGHT) {
      continue;
    }
    ctx.drawImage(getChunkCanvas(chunk, assets), x, y);
  }
}

function drawVillage(ctx, state, assets) {
  for (const chunk of state.chunks) {
    if (!chunk.village) continue;
    const baseX = chunk.village.x - state.camera.x;
    const baseY = chunk.village.y - state.camera.y;
    ctx.drawImage(assets.objects.type_forge, baseX, baseY, 112, 98);
    ctx.drawImage(assets.objects.object_village, baseX + 160, baseY - 20, 112, 98);
    ctx.drawImage(assets.objects.method_dojo, baseX + 310, baseY + 12, 112, 98);
  }
}

function drawResources(ctx, state, assets) {
  for (const resource of state.resources) {
    const x = resource.x - state.camera.x;
    const y = resource.y - state.camera.y;
    if (!visible(x, y, 64, 64)) continue;
    const image =
      resource.kind === "tree"
        ? assets.objects.tree
        : resource.kind === "ore"
          ? assets.objects.ore
          : assets.objects.rock;
    ctx.drawImage(image, x, y, 62, 58);
    drawNameplate(ctx, `${resource.amount}`, x + 31, y - 8, "#f6dfac");
  }
}

function drawChests(ctx, state, assets) {
  for (const chest of state.chests ?? []) {
    const x = chest.x - state.camera.x;
    const y = chest.y - state.camera.y;
    if (!visible(x, y, 64, 64)) continue;
    ctx.drawImage(assets.objects.collection_chest, x, y, 58, 54);
    const stored = chest.wood + chest.stone + chest.ore;
    drawNameplate(ctx, `Coffre (${stored})`, x + 29, y - 8, "#f6dfac");
  }
}

function drawNpcs(ctx, state, assets) {
  for (const npc of state.npcs) {
    const x = npc.x - state.camera.x;
    const y = npc.y - state.camera.y;
    if (!visible(x, y, FRAME_SIZE, FRAME_SIZE)) continue;
    const sprite = npc.role === "miner" ? "lynx" : npc.role === "merchant" ? "monkey" : "oracle_sage";
    if (npc.role === "miner") {
      drawMiningAnimation(ctx, assets, sprite, x - 20, y - 30);
    } else {
      drawSprite(ctx, assets.sprites[sprite], x, y, "down", 0);
    }
    drawNameplate(ctx, npc.name, x + 24, y - 10, "#fff8e8");
    if (npc.quest_marker) drawNameplate(ctx, npc.quest_marker, x + 42, y - 32, "#f6dfac");
  }
}

function drawOtherPlayers(ctx, state, assets) {
  for (const player of state.otherPlayers) {
    const worldX = player.renderX ?? player.x;
    const worldY = player.renderY ?? player.y;
    const x = worldX - state.camera.x;
    const y = worldY - state.camera.y;
    if (!visible(x, y, FRAME_SIZE, FRAME_SIZE)) continue;
    drawSprite(
      ctx,
      assets.sprites[player.skin_id] ?? assets.sprites.player,
      x,
      y,
      player.direction ?? "down",
      player.moving ? player.frame ?? 0 : 0,
    );
    drawNameplate(ctx, player.pseudo, x + 24, y - 10, "#d9e8d7");
  }
}

function drawPlayer(ctx, state, assets) {
  const x = state.player.x - state.camera.x;
  const y = state.player.y - state.camera.y;
  if (state.player.action === "mining") {
    drawMiningAnimation(ctx, assets, state.player.skin_id, x, y, state.player.actionMs ?? 0);
    drawNameplate(ctx, state.player.pseudo, x + 24, y - 10, "#f6dfac");
    return;
  }
  drawSprite(
    ctx,
    assets.sprites[state.player.skin_id] ?? assets.sprites.player,
    x,
    y,
    state.player.direction ?? "down",
    state.player.frame ?? 0,
  );
  drawNameplate(ctx, state.player.pseudo, x + 24, y - 10, "#f6dfac");
}

function drawChatBubbles(ctx, state) {
  const expire = (bubble) => {
    if (!bubble) return null;
    bubble.ttl -= 16;
    return bubble.ttl > 0 ? bubble : null;
  };

  state.selfBubble = expire(state.selfBubble);
  if (state.selfBubble && state.player) {
    drawBubble(ctx, state.selfBubble.text, state.player.x - state.camera.x + 24, state.player.y - state.camera.y - 28);
  }

  if (!state.bubbles) return;
  for (const player of state.otherPlayers) {
    const bubble = expire(state.bubbles[player.pseudo]);
    state.bubbles[player.pseudo] = bubble;
    if (!bubble) continue;
    const x = (player.renderX ?? player.x) - state.camera.x + 24;
    const y = (player.renderY ?? player.y) - state.camera.y - 28;
    drawBubble(ctx, bubble.text, x, y);
  }
}

function drawBubble(ctx, text, centerX, y) {
  ctx.font = "700 12px Avenir Next, Trebuchet MS, sans-serif";
  const width = Math.min(220, ctx.measureText(text).width + 16);
  const x = centerX - width / 2;
  drawPanel(ctx, x, y - 22, width, 22, "#fff8e8");
  ctx.fillStyle = "#17221f";
  const clipped = ctx.measureText(text).width + 16 > 220
    ? `${text.slice(0, 32)}…`
    : text;
  ctx.fillText(clipped, x + 8, y - 7);
}

function drawMiningAnimation(ctx, assets, skinId, x, y, actionMs) {
  const sheet = assets.animations[`${skinId}_mining`] ?? assets.animations.player_mining;
  // actionMs counts down from MINING_TOTAL_MS; map elapsed time to a frame so
  // the 18-frame sheet plays as a ~1s loop (canvas can't animate GIFs itself).
  const elapsed = MINING_DURATION_MS - actionMs;
  const frameDuration = MINING_DURATION_MS / MINING_FRAMES;
  const frame = Math.min(MINING_FRAMES - 1, Math.max(0, Math.floor(elapsed / frameDuration)));
  ctx.drawImage(sheet, frame * 96, 0, 96, 96, x, y, 48, 48);
}

function drawSprite(ctx, sheet, x, y, direction, frame) {
  const row = Math.max(0, DIRECTIONS.indexOf(direction));
  ctx.drawImage(sheet, frame * FRAME_SIZE, row * FRAME_SIZE, FRAME_SIZE, FRAME_SIZE, x, y, 48, 48);
}

function drawInteractionPrompt(ctx, state) {
  if (!state.nearbyInteraction) return;
  drawPanel(ctx, 300, 18, 360, 48, "#fff8e8");
  drawCentered(ctx, `E · ${state.nearbyInteraction.label}`, 480, 49, "#17221f", 16);
}

function drawHud(ctx, state) {
  drawPanel(ctx, 16, 16, 270, 92, "rgba(23, 34, 31, 0.9)");
  drawText(ctx, `Bois ${state.player.wood}`, 34, 48, "#fff8e8", 15);
  drawText(ctx, `Pierre ${state.player.stone}`, 122, 48, "#fff8e8", 15);
  drawText(ctx, `Minerai ${state.player.ore}`, 34, 78, "#fff8e8", 15);
}

function drawQuestPanel(ctx, state) {
  if (!state.quest) return;
  const step = state.quest.steps[state.quest.step_index] ?? state.quest.steps.at(-1);
  const target = questTargetLabel(state);
  const challenge = state.quest.sql_challenge;
  const choices = challenge?.choices ?? [];
  const cx = CANVAS_WIDTH - 312;
  const W = 276;
  const panelX = CANVAS_WIDTH - 330;
  const panelTop = 16;

  let stepText = step.text;
  if (step.required_count > 0) {
    stepText = `${step.text} (${state.quest.step_progress}/${step.required_count})`;
  }
  const hasGiver = state.quest.giver_name && state.quest.giver_block_x != null;
  const giverText = hasGiver
    ? `PNJ : ${state.quest.giver_name} — bloc ${state.quest.giver_block_x}, ${state.quest.giver_block_y}`
    : null;

  const stepLines = wrapLines(ctx, stepText, W);
  const targetLines = target ? wrapLines(ctx, target, W) : [];
  const promptLines = challenge ? wrapLines(ctx, challenge.prompt, W) : [];

  // Lay out sequentially so wrapped lines never overlap the next element.
  let y = 40;
  y += 20; // title
  y += 24; // step block start
  y += stepLines.length * 18;
  if (giverText) y += 22;
  if (targetLines.length) y += targetLines.length * 18 + 4;
  if (challenge) {
    y += 12 + 24; // "Question SQL" header
    y += promptLines.length * 17 + 10;
    y += choices.length * 38;
    y += 24; // footer
  }
  const panelHeight = y - panelTop;

  drawPanel(ctx, panelX, panelTop, 312, panelHeight, "#fff8e8");

  y = 40;
  drawText(ctx, `Quête ${state.quest.quest_number}/${state.quest.total_quests}`, cx, y, "#9b7447", 12);
  y += 20;
  drawText(ctx, state.quest.title, cx, y, "#7d2f2b", 16);
  y += 24;
  y = drawLines(ctx, stepLines, cx, y, 18, "#17221f");
  if (giverText) {
    drawText(ctx, giverText, cx, y, "#245f56", 12);
    y += 22;
  }
  if (targetLines.length) {
    y = drawLines(ctx, targetLines, cx, y, 18, "#17221f");
    y += 4;
  }
  if (challenge) {
    y += 12;
    drawText(ctx, "Question SQL", cx, y, "#7d2f2b", 15);
    y += 24;
    y = drawLines(ctx, promptLines, cx, y, 17, "#17221f");
    y += 10;
    choices.forEach((choice, index) => {
      drawPanel(ctx, cx, y, 276, 30, "#f1e1bd");
      drawWrapped(ctx, `${index + 1}. ${choice}`, cx + 8, y + 19, 262, 14, "#17221f");
      y += 38;
    });
    drawText(ctx, "Appuie 1, 2 ou 3 pour répondre", cx, y + 14, "#7d2f2b", 13);
  }
}

function drawMessage(ctx, state) {
  if (!state.message) return;
  state.message.ttl -= 16;
  if (state.message.ttl <= 0) {
    state.message = null;
    return;
  }
  drawPanel(ctx, 240, CANVAS_HEIGHT - 74, 480, 46, "rgba(23, 34, 31, 0.92)");
  drawCentered(ctx, state.message.text, 480, CANVAS_HEIGHT - 45, "#fff8e8", 14);
}

function drawBlockingMessage(ctx, message) {
  drawPanel(ctx, 220, 250, 520, 120, "#fff8e8");
  drawCentered(ctx, "Oracle requis", 480, 296, "#7d2f2b", 24);
  drawWrapped(ctx, message, 250, 328, 460, 20, "#17221f");
}

function drawNameplate(ctx, text, centerX, y, fill) {
  ctx.font = "800 11px Avenir Next, Trebuchet MS, sans-serif";
  const width = Math.ceil(ctx.measureText(text).width + 14);
  drawPanel(ctx, centerX - width / 2, y, width, 19, fill);
  drawCentered(ctx, text, centerX, y + 14, "#17221f", 11);
}

function drawPanel(ctx, x, y, width, height, fill) {
  ctx.fillStyle = "rgba(23, 34, 31, 0.24)";
  ctx.fillRect(x + 4, y + 4, width, height);
  ctx.fillStyle = fill;
  ctx.fillRect(x, y, width, height);
  ctx.strokeStyle = "#17221f";
  ctx.lineWidth = 3;
  ctx.strokeRect(x + 1.5, y + 1.5, width - 3, height - 3);
}

function drawText(ctx, text, x, y, color, size) {
  ctx.fillStyle = color;
  ctx.font = `900 ${size}px Avenir Next, Trebuchet MS, sans-serif`;
  ctx.fillText(text, x, y);
}

function drawCentered(ctx, text, centerX, y, color, size) {
  ctx.fillStyle = color;
  ctx.font = `900 ${size}px Avenir Next, Trebuchet MS, sans-serif`;
  ctx.fillText(text, centerX - ctx.measureText(text).width / 2, y);
}

function wrapLines(ctx, text, width) {
  ctx.font = "800 13px Avenir Next, Trebuchet MS, sans-serif";
  const lines = [];
  let line = "";
  for (const word of text.split(" ")) {
    const next = `${line}${word} `;
    if (ctx.measureText(next).width > width && line) {
      lines.push(line.trim());
      line = `${word} `;
    } else {
      line = next;
    }
  }
  if (line.trim()) lines.push(line.trim());
  return lines;
}

function drawLines(ctx, lines, x, y, lineHeight, color) {
  ctx.fillStyle = color;
  ctx.font = "800 13px Avenir Next, Trebuchet MS, sans-serif";
  let cursorY = y;
  for (const line of lines) {
    ctx.fillText(line, x, cursorY);
    cursorY += lineHeight;
  }
  return cursorY;
}

function drawWrapped(ctx, text, x, y, width, lineHeight, color) {
  ctx.fillStyle = color;
  ctx.font = "800 13px Avenir Next, Trebuchet MS, sans-serif";
  const words = text.split(" ");
  let line = "";
  let cursorY = y;
  for (const word of words) {
    const next = `${line}${word} `;
    if (ctx.measureText(next).width > width && line) {
      ctx.fillText(line.trim(), x, cursorY);
      cursorY += lineHeight;
      line = `${word} `;
    } else {
      line = next;
    }
  }
  if (line.trim()) ctx.fillText(line.trim(), x, cursorY);
}

function visible(x, y, width, height) {
  return x < CANVAS_WIDTH && x + width > 0 && y < CANVAS_HEIGHT && y + height > 0;
}
