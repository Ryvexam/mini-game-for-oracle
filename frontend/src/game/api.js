async function requestJson(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      ...(options.headers ?? {}),
    },
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail ?? "Oracle est indisponible.");
  }
  return response.json();
}

export async function fetchHealth() {
  return requestJson("/api/health");
}

export async function createSession(pseudo, skinId) {
  return requestJson("/api/game/session", {
    method: "POST",
    body: JSON.stringify({ pseudo, skin_id: skinId }),
  });
}

export async function fetchWorld(pseudo, chunkX, chunkY) {
  const params = new URLSearchParams({
    pseudo,
    chunk_x: String(chunkX),
    chunk_y: String(chunkY),
  });
  return requestJson(`/api/game/world?${params.toString()}`);
}

export async function saveMove(pseudo, x, y) {
  return requestJson("/api/game/move", {
    method: "POST",
    body: JSON.stringify({ pseudo, x: Math.round(x), y: Math.round(y) }),
  });
}

export async function harvest(pseudo, targetId) {
  return requestJson("/api/game/harvest", {
    method: "POST",
    body: JSON.stringify({ pseudo, target_id: targetId }),
  });
}

export async function talk(pseudo, npcId) {
  return requestJson("/api/game/talk", {
    method: "POST",
    body: JSON.stringify({ pseudo, npc_id: npcId }),
  });
}

export async function answerSql(pseudo, challengeId, answerIndex) {
  return requestJson("/api/game/sql-answer", {
    method: "POST",
    body: JSON.stringify({
      pseudo,
      challenge_id: challengeId,
      answer_index: answerIndex,
    }),
  });
}
