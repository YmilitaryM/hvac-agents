const BASE = '/api';

export async function fetchDailyReport(plantId?: string, date?: string) {
  const qs = new URLSearchParams();
  if (plantId) qs.set('plant_id', plantId);
  if (date) qs.set('date', date);
  const r = await fetch(`${BASE}/reports/daily?${qs}`);
  return r.json();
}

export async function fetchReportCsv(plantId?: string, date?: string) {
  const qs = new URLSearchParams();
  if (plantId) qs.set('plant_id', plantId);
  if (date) qs.set('date', date);
  const r = await fetch(`${BASE}/reports/csv?${qs}`);
  return r.json();
}

export async function fetchBenchmarking() {
  const r = await fetch(`${BASE}/benchmarking/plants`);
  return r.json();
}

export async function fetchBenchmarkingTrend(plantId: string) {
  const r = await fetch(`${BASE}/benchmarking/plant/${plantId}/trend`);
  return r.json();
}
