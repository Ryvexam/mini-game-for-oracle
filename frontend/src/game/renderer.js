import {
  CANVAS_HEIGHT,
  CANVAS_WIDTH,
  CHUNK_PIXELS,
  DIRECTIONS,
  FRAME_SIZE,
  TILE_SIZE,
} from "./constants.js";
import { questTargetLabel } from "./quests.js";

const TILE_BY_CODE = {
  g: "grass",
  p: "dirt",
  w: "water",
  r: "rocky",
  f: "flower_grass",
  v: "gravel",
  d: "dirt",
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
  drawNpcs(ctx, state, assets);
  drawOtherPlayers(ctx, state, assets);
  drawPlayer(ctx, state, assets);
  drawInteractionPrompt(ctx, state);
  drawHud(ctx, state);
  drawQuestPanel(ctx, state);
  drawMessage(ctx, state);
}

function updateCamera(state) {
  state.camera.x = state.player.x + FRAME_SIZE / 2 - CANVAS_WIDTH / 2;
  state.camera.y = state.player.y + FRAME_SIZE / 2 - CANVAS_HEIGHT / 2;
}

function drawChunks(ctx, state, assets) {
  for (const chunk of state.chunks) {
    const originX = chunk.chunk_x * CHUNK_PIXELS;
    const originY = chunk.chunk_y * CHUNK_PIXELS;
    chunk.tiles.forEach((row, tileY) => {
      for (let tileX = 0; tileX < row.length; tileX += 1) {
        const code = row[tileX];
        const name = TILE_BY_CODE[code] ?? "grass";
        const x = originX + tileX * TILE_SIZE - state.camera.x;
        const y = originY + tileY * TILE_SIZE - state.camera.y;
        if (x < -TILE_SIZE || y < -TILE_SIZE || x > CANVAS_WIDTH || y > CANVAS_HEIGHT) continue;
        ctx.drawImage(assets.tiles[name], x, y, TILE_SIZE, TILE_SIZE);
      }
    });
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
    const image = resource.kind === "tree" ? assets.objects.tree : assets.objects.rock;
    ctx.drawImage(image, x, y, 62, 58);
    drawNameplate(ctx, `${resource.amount}`, x + 31, y - 8, "#f6dfac");
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
    const x = player.x - state.camera.x;
    const y = player.y - state.camera.y;
    if (!visible(x, y, FRAME_SIZE, FRAME_SIZE)) continue;
    drawSprite(ctx, assets.sprites[player.skin_id] ?? assets.sprites.player, x, y, "down", 0);
    drawNameplate(ctx, player.pseudo, x + 24, y - 10, "#d9e8d7");
  }
}

function drawPlayer(ctx, state, assets) {
  const x = state.player.x - state.camera.x;
  const y = state.player.y - state.camera.y;
  if (state.player.action === "mining") {
    drawMiningAnimation(ctx, assets, state.player.skin_id, x - 20, y - 30);
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

function drawMiningAnimation(ctx, assets, skinId, x, y) {
  const image = assets.animations[`${skinId}_mining`] ?? assets.animations.player_mining;
  ctx.drawImage(image, x, y, 96, 96);
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
  drawPanel(ctx, CANVAS_WIDTH - 330, 16, 312, state.quest.sql_challenge ? 264 : 128, "#fff8e8");
  drawText(ctx, state.quest.title, CANVAS_WIDTH - 312, 48, "#7d2f2b", 16);
  drawWrapped(ctx, step.text, CANVAS_WIDTH - 312, 76, 276, 18, "#17221f");
  if (target) drawWrapped(ctx, target, CANVAS_WIDTH - 312, 112, 276, 18, "#17221f");
  if (state.quest.sql_challenge) {
    drawText(ctx, "Question SQL", CANVAS_WIDTH - 312, 146, "#7d2f2b", 15);
    drawWrapped(ctx, state.quest.sql_challenge.prompt, CANVAS_WIDTH - 312, 170, 276, 17, "#17221f");
    drawText(ctx, "Appuie 1, 2 ou 3 pour répondre", CANVAS_WIDTH - 312, 238, "#17221f", 13);
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
