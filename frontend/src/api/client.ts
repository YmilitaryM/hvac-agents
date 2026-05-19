async function apiFetch(url: string, opts?: RequestInit) {
  const r = await fetch(url, opts);
  if (!r.ok) {
    const body = await r.text().catch(() => '');
    throw new Error(`HTTP ${r.status}: ${body || r.statusText}`);
  }
  if (r.status === 204) return null;
  return r.json();
}

export { apiFetch };
