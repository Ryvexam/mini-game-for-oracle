export function connectPresence(state) {
  if (!state?.player || state.presenceSocket) return;
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const params = new URLSearchParams({
    pseudo: state.pseudo,
    skin_id: state.player.skin_id,
  });
  const socket = new WebSocket(`${protocol}//${window.location.host}/ws/game?${params.toString()}`);
  state.presenceSocket = socket;

  socket.addEventListener("message", (event) => {
    const payload = JSON.parse(event.data);
    if (payload.type !== "presence") return;
    state.otherPlayers = payload.players.filter((player) => player.pseudo !== state.pseudo);
  });

  socket.addEventListener("close", () => {
    state.presenceSocket = null;
  });
}

export function sendPresence(state) {
  const socket = state?.presenceSocket;
  if (!socket || socket.readyState !== WebSocket.OPEN || !state.player) return;
  socket.send(
    JSON.stringify({
      x: Math.round(state.player.x),
      y: Math.round(state.player.y),
      skin_id: state.player.skin_id,
    }),
  );
}
