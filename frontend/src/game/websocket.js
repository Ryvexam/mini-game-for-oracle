const RECONNECT_BASE_MS = 800;
const RECONNECT_MAX_MS = 8000;
const HEARTBEAT_MS = 15000;

export function connectPresence(state) {
  if (!state?.player) return;
  if (state.presenceSocket && state.presenceSocket.readyState <= WebSocket.OPEN) return;
  state.blockReconnect = false;

  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const params = new URLSearchParams({
    pseudo: state.pseudo,
    skin_id: state.player.skin_id,
  });
  const socket = new WebSocket(`${protocol}//${window.location.host}/ws/game?${params.toString()}`);
  state.presenceSocket = socket;

  socket.addEventListener("open", () => {
    state.presenceReconnectMs = RECONNECT_BASE_MS;
    state.connected = true;
    clearInterval(state.presenceHeartbeat);
    state.presenceHeartbeat = setInterval(() => {
      if (socket.readyState === WebSocket.OPEN) socket.send(JSON.stringify({ type: "ping" }));
    }, HEARTBEAT_MS);
  });

  socket.addEventListener("message", (event) => {
    let payload;
    try {
      payload = JSON.parse(event.data);
    } catch {
      return;
    }
    handleMessage(state, payload);
  });

  socket.addEventListener("close", () => {
    state.presenceSocket = null;
    state.connected = false;
    clearInterval(state.presenceHeartbeat);
    if (!state.blockReconnect) scheduleReconnect(state);
  });

  socket.addEventListener("error", () => socket.close());
}

function handleMessage(state, payload) {
  if (payload.type === "presence") {
    const incoming = payload.players.filter((player) => player.pseudo !== state.pseudo);
    state.otherPlayers = incoming.map((player) => {
      const prev = state.otherPlayers.find((item) => item.pseudo === player.pseudo);
      return {
        ...player,
        renderX: prev?.renderX ?? player.x,
        renderY: prev?.renderY ?? player.y,
      };
    });
  } else if (payload.type === "chat") {
    pushChat(state, { pseudo: payload.pseudo, text: payload.text });
    setBubble(state, payload.pseudo, payload.text);
  } else if (payload.type === "system") {
    pushChat(state, { system: true, text: payload.text });
  } else if (payload.type === "world_reset") {
    state.worldResetSeed = payload.seed;
  } else if (payload.type === "duplicate") {
    state.duplicate = payload.text ?? "Ce pseudo est déjà connecté.";
    state.blockReconnect = true;
  }
}

function setBubble(state, pseudo, text) {
  const bubble = { text: String(text).slice(0, 80), ttl: 5000 };
  if (pseudo === state.pseudo) {
    state.selfBubble = bubble;
    return;
  }
  state.bubbles = state.bubbles ?? {};
  state.bubbles[pseudo] = bubble;
}

export function disconnectPresence(state) {
  state.blockReconnect = true;
  clearInterval(state.presenceHeartbeat);
  const socket = state.presenceSocket;
  state.presenceSocket = null;
  state.connected = false;
  if (socket && socket.readyState <= WebSocket.OPEN) socket.close();
}

function pushChat(state, entry) {
  state.chatLog = [...(state.chatLog ?? []), { ...entry, ttl: 9000 }].slice(-40);
}

function scheduleReconnect(state) {
  if (!state.player) return;
  const delay = state.presenceReconnectMs ?? RECONNECT_BASE_MS;
  state.presenceReconnectMs = Math.min(delay * 2, RECONNECT_MAX_MS);
  setTimeout(() => connectPresence(state), delay);
}

export function sendPresence(state) {
  const socket = state?.presenceSocket;
  if (!socket || socket.readyState !== WebSocket.OPEN || !state.player) return;
  socket.send(
    JSON.stringify({
      type: "move",
      x: Math.round(state.player.x),
      y: Math.round(state.player.y),
      direction: state.player.direction ?? "down",
      frame: state.player.frame ?? 0,
      moving: Boolean(state.player.moving),
      skin_id: state.player.skin_id,
    }),
  );
}

export function sendChat(state, text) {
  const socket = state?.presenceSocket;
  const trimmed = text.trim();
  if (!socket || socket.readyState !== WebSocket.OPEN || !trimmed) return;
  socket.send(JSON.stringify({ type: "chat", text: trimmed.slice(0, 160) }));
}
