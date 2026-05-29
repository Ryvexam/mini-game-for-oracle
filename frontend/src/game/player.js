import { PLAYER_SPEED } from "./constants.js";

export function updatePlayer(state, input, delta) {
  if (!state.player) return;
  const previousX = state.player.x;
  const previousY = state.player.y;
  let dx = 0;
  let dy = 0;
  if (input.isDown("left")) dx -= 1;
  if (input.isDown("right")) dx += 1;
  if (input.isDown("up")) dy -= 1;
  if (input.isDown("down")) dy += 1;

  if (dx !== 0 && dy !== 0) {
    dx *= 0.707;
    dy *= 0.707;
  }

  state.player.moving = dx !== 0 || dy !== 0;
  if (Math.abs(dx) > Math.abs(dy)) state.player.direction = dx < 0 ? "left" : "right";
  if (Math.abs(dy) > Math.abs(dx)) state.player.direction = dy < 0 ? "up" : "down";

  state.player.x += dx * PLAYER_SPEED * delta;
  state.player.y += dy * PLAYER_SPEED * delta;
  if (state.player.x !== previousX || state.player.y !== previousY) {
    state.positionDirty = true;
  }

  state.player.animationMs = (state.player.animationMs ?? 0) + delta;
  if (state.player.animationMs > 130) {
    state.player.animationMs = 0;
    state.player.frame = state.player.moving ? ((state.player.frame ?? 0) + 1) % 4 : 0;
  }
}
