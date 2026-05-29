import { CANVAS_HEIGHT, CANVAS_WIDTH, CHUNK_TILES, TILE_SIZE } from "./constants.js";

const MAP_RADIUS = 30;
const PIXEL_SIZE = 3;
const OFFSET = 6;
const TILE_COLORS = {
  g: "#527d3d",
  p: "#c9b07a",
  w: "#1f7f94",
  r: "#6f6f66",
  f: "#6aa343",
  v: "#8d8773",
  d: "#9b7447",
  s: "#b9bdc4",
};

const MINI_CFG = { radius: MAP_RADIUS, pixel: PIXEL_SIZE, offset: OFFSET, viewport: true };

export function renderMiniMap(ctx, state) {
  drawMap(ctx, state, MINI_CFG);
}

// Static pre-rendered world map: 2001x2001 tiles, origin tile (-1000,-1000).
export const WORLD_MAP_ORIGIN = -1000;
export const WORLD_MAP_TILES = 2001;

const worldMapImage = new Image();
let worldMapLoaded = false;
worldMapImage.addEventListener("load", () => {
  worldMapLoaded = true;
});
worldMapImage.src = "/world-map.png";

export function reloadWorldMap(version) {
  worldMapLoaded = false;
  worldMapImage.src = `/world-map.png?v=${version}`;
}

export function renderBigMap(ctx, state) {
  const canvasW = ctx.canvas.width;
  const canvasH = ctx.canvas.height;
  ctx.clearRect(0, 0, canvasW, canvasH);
  ctx.fillStyle = "#1b2b27";
  ctx.fillRect(0, 0, canvasW, canvasH);

  if (!worldMapLoaded) {
    ctx.fillStyle = "#cdd9c8";
    ctx.font = "16px system-ui, sans-serif";
    ctx.fillText("Chargement de la carte…", 20, 30);
    return;
  }

  const view = state.mapView ?? WORLD_MAP_TILES; // tiles visible across canvas
  const center = state.mapCenter ?? { x: 0, y: 0 };
  const sx = center.x - WORLD_MAP_ORIGIN - view / 2;
  const sy = center.y - WORLD_MAP_ORIGIN - view / 2;

  ctx.imageSmoothingEnabled = false;
  ctx.drawImage(worldMapImage, sx, sy, view, view, 0, 0, canvasW, canvasH);

  const scale = canvasW / view;
  const marker = (worldX, worldY, color, size) => {
    const tileX = Math.floor(worldX / TILE_SIZE);
    const tileY = Math.floor(worldY / TILE_SIZE);
    const px = (tileX - (center.x - view / 2)) * scale;
    const py = (tileY - (center.y - view / 2)) * scale;
    if (px < 0 || py < 0 || px > canvasW || py > canvasH) return;
    ctx.fillStyle = color;
    ctx.fillRect(px - (size >> 1), py - (size >> 1), size, size);
  };

  for (const npc of state.npcs ?? []) marker(npc.x, npc.y, "#f05d4f", 7);
  for (const chest of state.chests ?? []) marker(chest.x, chest.y, "#e0a93f", 7);
  for (const other of state.otherPlayers ?? []) marker(other.x, other.y, "#7fd3ff", 7);
  if (state.player) marker(state.player.x, state.player.y, "#ffffff", 9);
}

function drawMap(ctx, state, cfg) {
  if (!state?.player) {
    drawEmpty(ctx);
    return;
  }
  const { radius, pixel, offset } = cfg;
  const playerTileX = Math.floor((state.player.x + 24) / TILE_SIZE);
  const playerTileY = Math.floor((state.player.y + 24) / TILE_SIZE);
  const index = buildTileIndex(state.chunks);

  ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
  ctx.fillStyle = "#1b2b27";
  ctx.fillRect(0, 0, ctx.canvas.width, ctx.canvas.height);

  for (let dy = -radius; dy <= radius; dy += 1) {
    for (let dx = -radius; dx <= radius; dx += 1) {
      const code = tileFromIndex(index, playerTileX + dx, playerTileY + dy);
      if (!code) continue;
      ctx.fillStyle = TILE_COLORS[code] ?? "#36513c";
      ctx.fillRect((dx + radius) * pixel + offset, (dy + radius) * pixel + offset, pixel, pixel);
    }
  }

  if (cfg.viewport) drawViewport(ctx, cfg);
  drawMarkers(ctx, state, playerTileX, playerTileY, cfg);

  const span = (radius * 2 + 1) * pixel;
  ctx.strokeStyle = "#0f1714";
  ctx.lineWidth = 2;
  ctx.strokeRect(offset - 1, offset - 1, span + 2, span + 2);
}

export function formatCoordinates(player) {
  if (!player) return "Bloc 0, 0";
  const tileX = Math.floor((player.x + 24) / TILE_SIZE);
  const tileY = Math.floor((player.y + 24) / TILE_SIZE);
  return `Bloc ${tileX}, ${tileY}`;
}

function buildTileIndex(chunks) {
  const index = new Map();
  for (const chunk of chunks) {
    index.set(`${chunk.chunk_x},${chunk.chunk_y}`, chunk.tiles);
  }
  return index;
}

function tileFromIndex(index, tileX, tileY) {
  const chunkX = Math.floor(tileX / CHUNK_TILES);
  const chunkY = Math.floor(tileY / CHUNK_TILES);
  const tiles = index.get(`${chunkX},${chunkY}`);
  if (!tiles) return null;
  return tiles[mod(tileY, CHUNK_TILES)]?.[mod(tileX, CHUNK_TILES)] ?? null;
}

function drawEmpty(ctx) {
  ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
  ctx.fillStyle = "#1b2b27";
  ctx.fillRect(0, 0, ctx.canvas.width, ctx.canvas.height);
}

function drawViewport(ctx, cfg) {
  const { radius, pixel, offset } = cfg;
  const halfW = CANVAS_WIDTH / 2 / TILE_SIZE;
  const halfH = CANVAS_HEIGHT / 2 / TILE_SIZE;
  ctx.strokeStyle = "rgba(255, 248, 232, 0.55)";
  ctx.lineWidth = 1;
  ctx.strokeRect(
    (radius - halfW) * pixel + offset,
    (radius - halfH) * pixel + offset,
    halfW * 2 * pixel,
    halfH * 2 * pixel,
  );
}

function drawMarkers(ctx, state, playerTileX, playerTileY, cfg) {
  for (const chunk of state.chunks) {
    if (chunk.village) {
      drawWorldMarker(ctx, chunk.village.x, chunk.village.y, playerTileX, playerTileY, "#ffd36b", 4, cfg);
    }
  }
  for (const resource of state.resources) {
    const color = resource.kind === "tree" ? "#6fae4a" : resource.kind === "ore" ? "#c98bff" : "#cbb27a";
    drawWorldMarker(ctx, resource.x, resource.y, playerTileX, playerTileY, color, 1, cfg);
  }
  for (const chest of state.chests ?? []) {
    drawWorldMarker(ctx, chest.x, chest.y, playerTileX, playerTileY, "#e0a93f", 3, cfg);
  }
  for (const npc of state.npcs) {
    drawWorldMarker(ctx, npc.x, npc.y, playerTileX, playerTileY, "#f05d4f", 3, cfg);
  }
  for (const player of state.otherPlayers) {
    drawWorldMarker(ctx, player.x, player.y, playerTileX, playerTileY, "#7fd3ff", 3, cfg);
  }
  drawWorldMarker(ctx, state.player.x, state.player.y, playerTileX, playerTileY, "#ffffff", 4, cfg);
}

function drawWorldMarker(ctx, worldX, worldY, playerTileX, playerTileY, color, size, cfg) {
  const { radius, pixel, offset } = cfg;
  const dx = Math.floor(worldX / TILE_SIZE) - playerTileX;
  const dy = Math.floor(worldY / TILE_SIZE) - playerTileY;
  if (Math.abs(dx) > radius || Math.abs(dy) > radius) return;
  const screenX = (dx + radius) * pixel + offset;
  const screenY = (dy + radius) * pixel + offset;
  ctx.fillStyle = color;
  ctx.fillRect(screenX - Math.floor(size / 2), screenY - Math.floor(size / 2), size, size);
}

function mod(value, size) {
  return ((value % size) + size) % size;
}
