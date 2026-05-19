const BASE = '/api/rl';

export async function getRLStatus() {
  const r = await fetch(`${BASE}/status`);
  return r.json();
}

export async function runInference(state?: number[]) {
  const r = await fetch(`${BASE}/inference`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ state }),
  });
  return r.json();
}

export async function startTraining(data: {
  plant_id: string;
  num_episodes?: number;
  steps_per_episode?: number;
}) {
  const r = await fetch(`${BASE}/train`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  return r.json();
}

export async function listCheckpoints() {
  const r = await fetch(`${BASE}/checkpoints`);
  return r.json();
}
