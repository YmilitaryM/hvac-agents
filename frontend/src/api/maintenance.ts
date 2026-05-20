const BASE = '/api/maintenance';

export interface DegradationRequest {
  edge_id: string;
  equipment_id: string;
  equipment_type: string;
  design_cop?: number;
  cop_window: number[];
  approach_temp_avg?: number;
  vibration_window?: number[];
}

export interface DegradationResult {
  severity: 'healthy' | 'degrading' | 'critical';
  cop_degradation_pct: number;
  cusum_triggered: boolean;
  recommended_action: string;
}

export interface PredictRequest {
  cop_current: number;
  vibration_rms: number;
  approach_temp: number;
}

export interface PredictResult {
  failure_probability: number;
}

export async function evaluateDegradation(body: DegradationRequest): Promise<DegradationResult> {
  const r = await fetch(`${BASE}/evaluate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error('Failed to evaluate degradation');
  return r.json();
}

export async function predictFailure(body: PredictRequest): Promise<PredictResult> {
  const r = await fetch(`${BASE}/predict`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error('Failed to predict failure');
  return r.json();
}
