const BASE = '/api/versions';

export async function fetchVersions(entityType: string, entityId: string) {
  const r = await fetch(`${BASE}/${entityType}/${entityId}`);
  return r.json();
}

export async function getVersion(entityType: string, entityId: string, version: number) {
  const r = await fetch(`${BASE}/${entityType}/${entityId}/${version}`);
  return r.json();
}

export async function getVersionDiff(entityType: string, entityId: string, version: number) {
  const r = await fetch(`${BASE}/${entityType}/${entityId}/${version}/diff`);
  return r.json();
}

export async function createSnapshot(data: {
  entity_type: string;
  entity_id: string;
  data: Record<string, unknown>;
  change_reason?: string;
}) {
  const r = await fetch(`${BASE}/snapshot`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  return r.json();
}

export async function rollbackVersion(entityType: string, entityId: string, targetVersion: number, reason?: string) {
  const r = await fetch(`${BASE}/${entityType}/${entityId}/rollback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ target_version: targetVersion, reason: reason || '', validate: true }),
  });
  return r.json();
}
