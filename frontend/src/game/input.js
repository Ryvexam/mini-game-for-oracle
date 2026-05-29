export function createInput() {
  const pressed = new Set();
  const consumed = new Set();

  window.addEventListener("keydown", (event) => {
    if (isTextInput(event.target)) return;
    const key = normalize(event.key);
    pressed.add(key);
    if (["up", "down", "left", "right", "interact"].includes(key)) {
      event.preventDefault();
    }
  });

  window.addEventListener("keyup", (event) => {
    if (isTextInput(event.target)) return;
    pressed.delete(normalize(event.key));
  });

  return {
    pressed,
    isDown(key) {
      return pressed.has(key);
    },
    consume(action) {
      if (!pressed.has(action) || consumed.has(action)) return false;
      consumed.add(action);
      setTimeout(() => consumed.delete(action), 180);
      return true;
    },
  };
}

function isTextInput(target) {
  return target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement;
}

function normalize(key) {
  const lower = key.toLowerCase();
  if (lower === "arrowup" || lower === "w") return "up";
  if (lower === "arrowdown" || lower === "s") return "down";
  if (lower === "arrowleft" || lower === "a") return "left";
  if (lower === "arrowright" || lower === "d") return "right";
  if (lower === "e" || lower === "enter" || lower === " ") return "interact";
  return lower;
}
