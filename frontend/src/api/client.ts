let authToken: string | null = null;

try {
  authToken = localStorage.getItem('auth_token');
} catch {
  // localStorage not available (e.g., test environment before jsdom init)
}

export function setAuthToken(token: string | null) {
  authToken = token;
  try {
    if (token) {
      localStorage.setItem('auth_token', token);
    } else {
      localStorage.removeItem('auth_token');
    }
  } catch {
    // localStorage not available
  }
}

function buildHeaders(extra?: Record<string, string>): Record<string, string> {
  const headers: Record<string, string> = { ...extra };
  if (authToken) {
    headers['Authorization'] = `Bearer ${authToken}`;
  }
  return headers;
}

async function apiFetch(url: string, opts?: RequestInit) {
  const r = await fetch(url, opts);
  if (!r.ok) {
    const body = await r.text().catch(() => '');
    throw new Error(`HTTP ${r.status}: ${body || r.statusText}`);
  }
  if (r.status === 204) return null;
  return r.json();
}

const apiClient = {
  get: (url: string) => apiFetch(url, { headers: buildHeaders() }),
  post: (url: string, body?: unknown) =>
    apiFetch(url, {
      method: 'POST',
      headers: buildHeaders({ 'Content-Type': 'application/json' }),
      body: body ? JSON.stringify(body) : undefined,
    }),
  put: (url: string, body?: unknown) =>
    apiFetch(url, {
      method: 'PUT',
      headers: buildHeaders({ 'Content-Type': 'application/json' }),
      body: body ? JSON.stringify(body) : undefined,
    }),
  delete: (url: string) => apiFetch(url, { method: 'DELETE', headers: buildHeaders() }),
};

export async function downloadFile(url: string, filename: string) {
  const headers: Record<string, string> = {};
  try {
    if (authToken) headers['Authorization'] = `Bearer ${authToken}`;
  } catch {}

  const resp = await fetch(url, { headers });
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  const blob = await resp.blob();
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}

export { apiFetch, apiClient };
