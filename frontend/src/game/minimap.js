import { CHUNK_TILES, TILE_SIZE } from "./constants.js";

const MAP_RADIUS = 30;
const MAP_SIZE = MAP_RADIUS * 2 + 1;
const PIXEL_SIZE = 3;
const TILE_COLORS = {
  g: "#527d3d",
  p: "#9b7447",
  w: "#1f7f94",
  r: "#6f6f66",
  f: "#638f3f",
  v: "#8d8773",
  d: "#9b7447",
};

export function renderMiniMap(ctx, state) {
  if (!state?.player) {
    drawEmpty(ctx);
    return;
  }

  const playerTileX = Math.floor(state.player.x / TILE_SIZE);
  const playerTileY = Math.floor(state.player.y / TILE_SIZE);
  ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
  ctx.fillStyle = "#253a34";
  ctx.fillRect(0, 0, ctx.canvas.width, ctx.canvas.height);

  for (let dy = -MAP_RADIUS; dy <= MAP_RADIUS; dy += 1) {
    for (let dx = -MAP_RADIUS; dx <= MAP_RADIUS; dx += 1) {
      const tileX = playerTileX + dx;
      const tileY = playerTileY + dy;
      const code = tileAt(state.chunks, tileX, tileY);
      const screenX = (dx + MAP_RADIUS) * PIXEL_SIZE + 4;
      const screenY = (dy + MAP_RADIUS) * PIXEL_SIZE + 4;
      ctx.fillStyle = TILE_COLORS[code] ?? "#36513c";
      ctx.fillRect(screenX, screenY, PIXEL_SIZE, PIXEL_SIZE);
    }
  }

  drawMarkers(ctx, state, playerTileX, playerTileY);
  ctx.strokeStyle = "#17221f";
  ctx.lineWidth = 2;
  ctx.strokeRect(3, 3, MAP_SIZE * PIXEL_SIZE + 2, MAP_SIZE * PIXEL_SIZE + 2);
}

export function formatCoordinates(player) {
  if (!player) return "Bloc 0, 0";
  const tileX = Math.floor(player.x / TILE_SIZE);
  const tileY = Math.floor(player.y / TILE_SIZE);
  return `Bloc ${tileX}, ${tileY}`;
}

function drawEmpty(ctx) {
  ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
  ctx.fillStyle = "#253a34";
  ctx.fillRect(0, 0, ctx.canvas.width, ctx.canvas.height);
}

function tileAt(chunks, tileX, tileY) {
  const chunkX = Math.floor(tileX / CHUNK_TILES);
  const chunkY = Math.floor(tileY / CHUNK_TILES);
  const localX = mod(tileX, CHUNK_TILES);
  const localY = mod(tileY, CHUNK_TILES);
  const chunk = chunks.find((item) => item.chunk_x === chunkX && item.chunk_y === chunkY);
  return chunk?.tiles?.[localY]?.[localX] ?? "g";
}

function drawMarkers(ctx, state, playerTileX, playerTileY) {
  for (const resource of state.resources) {
    drawWorldMarker(ctx, resource.x, resource.y, playerTileX, playerTileY, "#d7c777", 1);
  }
  for (const npc of state.npcs) {
    drawWorldMarker(ctx, npc.x, npc.y, playerTileX, playerTileY, "#f05d4f", 2);
  }
  for (const player of state.otherPlayers) {
    drawWorldMarker(ctx, player.x, player.y, playerTileX, playerTileY, "#f6dfac", 2);
  }
  drawWorldMarker(ctx, state.player.x, state.player.y, playerTileX, playerTileY, "#ffffff", 3);
}

function drawWorldMarker(ctx, worldX, worldY, playerTileX, playerTileY, color, size) {
  const tileX = Math.floor(worldX / TILE_SIZE);
  const tileY = Math.floor(worldY / TILE_SIZE);
  const dx = tileX - playerTileX;
  const dy = tileY - playerTileY;
  if (Math.abs(dx) > MAP_RADIUS || Math.abs(dy) > MAP_RADIUS) return;
  const screenX = (dx + MAP_RADIUS) * PIXEL_SIZE + 4;
  const screenY = (dy + MAP_RADIUS) * PIXEL_SIZE + 4;
  ctx.fillStyle = color;
  ctx.fillRect(screenX - Math.floor(size / 2), screenY - Math.floor(size / 2), size, size);
}

function mod(value, size) {
  return ((value % size) + size) % size;
}
