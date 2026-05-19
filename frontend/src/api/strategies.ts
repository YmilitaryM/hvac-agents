const BASE = '/api/strategies';

export async function fetchStrategies() {
  const r = await fetch(BASE);
  return r.json();
}

export async function getStrategy(id: string) {
  const r = await fetch(`${BASE}/${id}`);
  return r.json();
}

export async function createStrategy(data: {
  name: string;
  description?: string;
  config: Record<string, unknown>;
}) {
  const r = await fetch(BASE, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  return r.json();
}

export async function updateStrategyStatus(id: string, status: string) {
  const r = await fetch(`${BASE}/${id}/status`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status }),
  });
  return r.json();
}

export async function deleteStrategy(id: string) {
  await fetch(`${BASE}/${id}`, { method: 'DELETE' });
}
