const BASE = '/api';

export async function runSimulation(data: {
  plant_id: string;
  weather_hour?: number;
  steps?: number;
}) {
  const r = await fetch(`${BASE}/simulation/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  return r.json();
}

export async function fetchFaults() {
  const r = await fetch(`${BASE}/faults`);
  return r.json();
}

export async function injectFault(data: {
  device_id: string;
  fault_type: string;
  severity: number;
}) {
  const r = await fetch(`${BASE}/faults/inject`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  return r.json();
}

export async function removeFault(id: string) {
  const r = await fetch(`${BASE}/faults/remove/${id}`, { method: 'POST' });
  return r.json();
}

export async function createWhatIf(data: {
  plant_id: string;
  scenarios: Array<{ name: string; config: Record<string, unknown> }>;
}) {
  const r = await fetch(`${BASE}/simulation/whatif`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  return r.json();
}

export async function getWhatIfStatus(jobId: string) {
  const r = await fetch(`${BASE}/simulation/whatif/${jobId}`);
  return r.json();
}

export async function getWhatIfReport(jobId: string) {
  const r = await fetch(`${BASE}/simulation/whatif/${jobId}/report`);
  return r.json();
}

export async function fetchDiagnostics() {
  const r = await fetch(`${BASE}/faults/diagnostics`);
  return r.json();
}
