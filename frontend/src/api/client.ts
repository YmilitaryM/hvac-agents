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
  get: (url: string) => apiFetch(url),
  post: (url: string, body?: unknown) => apiFetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: body ? JSON.stringify(body) : undefined }),
  put: (url: string, body?: unknown) => apiFetch(url, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: body ? JSON.stringify(body) : undefined }),
  delete: (url: string) => apiFetch(url, { method: 'DELETE' }),
};

export { apiFetch, apiClient };
