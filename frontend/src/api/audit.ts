const BASE = '/api/audit';

export async function fetchAuditLogs(params?: {
  user_id?: string;
  action?: string;
  resource_type?: string;
  limit?: number;
}) {
  const qs = new URLSearchParams();
  if (params?.user_id) qs.set('user_id', params.user_id);
  if (params?.action) qs.set('action', params.action);
  if (params?.resource_type) qs.set('resource_type', params.resource_type);
  if (params?.limit) qs.set('limit', String(params.limit));
  const r = await fetch(`${BASE}/logs?${qs}`);
  return r.json();
}

export async function getAuditLog(id: string) {
  const r = await fetch(`${BASE}/logs/${id}`);
  return r.json();
}

export async function exportAuditLogs() {
  const r = await fetch(`${BASE}/logs/export`);
  return r.json();
}
