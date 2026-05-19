const BASE = '/api/monitoring';

export async function fetchKpi() {
  const r = await fetch(`${BASE}/kpi`);
  return r.json();
}

export async function fetchSnapshot() {
  const r = await fetch(`${BASE}/snapshot`);
  return r.json();
}

export async function fetchSnapshots(params?: { plant_id?: string; limit?: number }) {
  const qs = new URLSearchParams();
  if (params?.plant_id) qs.set('plant_id', params.plant_id);
  if (params?.limit) qs.set('limit', String(params.limit));
  const r = await fetch(`${BASE}/snapshots?${qs}`);
  return r.json();
}

export async function fetchAlerts(params?: { severity?: string; acknowledged?: boolean }) {
  const qs = new URLSearchParams();
  if (params?.severity) qs.set('severity', params.severity);
  if (params?.acknowledged !== undefined) qs.set('acknowledged', String(params.acknowledged));
  const r = await fetch(`${BASE}/alerts?${qs}`);
  return r.json();
}

export async function acknowledgeAlert(id: string) {
  const r = await fetch(`${BASE}/alerts/${id}/acknowledge`, { method: 'PUT' });
  return r.json();
}

export async function fetchHealth() {
  const r = await fetch(`${BASE}/health`);
  return r.json();
}
