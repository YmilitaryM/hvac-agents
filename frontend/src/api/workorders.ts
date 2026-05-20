const BASE = '/api/workorders';

export interface WorkOrder {
  id: string;
  edge_id: string;
  equipment_id: string;
  severity: 'critical' | 'warning' | 'info';
  title: string;
  description: string;
  status: 'open' | 'acknowledged' | 'in_progress' | 'resolved' | 'closed' | 'rejected';
  assigned_to: string | null;
  source: 'auto' | 'manual';
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
}

export async function fetchWorkOrders(params?: { status?: string; severity?: string; edge_id?: string; search?: string }) {
  const qs = new URLSearchParams();
  if (params?.status) qs.set('status', params.status);
  if (params?.severity) qs.set('severity', params.severity);
  if (params?.edge_id) qs.set('edge_id', params.edge_id);
  if (params?.search) qs.set('search', params.search);
  const r = await fetch(`${BASE}/${qs.toString() ? '?' + qs.toString() : ''}`);
  if (!r.ok) throw new Error('Failed to fetch work orders');
  return r.json();
}

export async function createWorkOrder(body: {
  edge_id: string;
  equipment_id: string;
  severity: string;
  title: string;
  description: string;
  source?: string;
}) {
  const r = await fetch(`${BASE}/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error('Failed to create work order');
  return r.json();
}

export async function fetchWorkOrderDetail(woId: string) {
  const r = await fetch(`${BASE}/${woId}`);
  if (!r.ok) throw new Error('Failed to fetch work order');
  return r.json();
}

export async function transitionWorkOrder(woId: string, toStatus: string, note?: string) {
  const r = await fetch(`${BASE}/${woId}/transition`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ to_status: toStatus, note }),
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    throw new Error(err.detail || 'Transition failed');
  }
  return r.json();
}
