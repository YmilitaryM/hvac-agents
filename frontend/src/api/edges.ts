const BASE = '/api/edges';

export interface EdgeDevice {
  edge_id: string;
  plant_id: string;
  mode: string;
  status: string;
  last_heartbeat: string | null;
  version: string;
  registered_at: string;
}

export async function fetchEdges(params?: { status?: string; search?: string }) {
  const qs = new URLSearchParams();
  if (params?.status) qs.set('status', params.status);
  if (params?.search) qs.set('search', params.search);
  const r = await fetch(`${BASE}/${qs.toString() ? '?' + qs.toString() : ''}`);
  if (!r.ok) throw new Error('Failed to fetch edges');
  return r.json();
}

export async function registerEdge(body: { edge_id: string; plant_id: string; mode: string }) {
  const r = await fetch(`${BASE}/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error('Failed to register edge');
  return r.json();
}

export async function fetchEdgeStatus(edgeId: string) {
  const r = await fetch(`${BASE}/${edgeId}/status`);
  if (!r.ok) throw new Error('Failed to fetch edge status');
  return r.json();
}

export async function fetchEdgeConfig(edgeId: string) {
  const r = await fetch(`${BASE}/${edgeId}/config`);
  if (!r.ok) throw new Error('Failed to fetch edge config');
  return r.json();
}

export async function setEdgeConfig(edgeId: string, config: Record<string, unknown>) {
  const r = await fetch(`${BASE}/${edgeId}/config`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  });
  if (!r.ok) throw new Error('Failed to set edge config');
  return r.json();
}

export async function fetchOTATasks(edgeId: string) {
  const r = await fetch(`${BASE}/${edgeId}/ota/`);
  if (!r.ok) throw new Error('Failed to fetch OTA tasks');
  return r.json();
}

export async function createOTATask(edgeId: string, body: { version: string; url?: string }) {
  const r = await fetch(`${BASE}/${edgeId}/ota/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error('Failed to create OTA task');
  return r.json();
}

export async function deleteEdge(edgeId: string) {
  const r = await fetch(`${BASE}/${edgeId}`, { method: 'DELETE' });
  if (!r.ok) throw new Error('Failed to delete edge');
  return r.json();
}
