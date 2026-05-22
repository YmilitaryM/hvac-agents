import { apiClient } from './client';

export interface HealthOverview {
  plant_id: number;
  overall_health: number;
  equipment_health: Array<{
    equipment_id: number; name: string; overall_score: number; status: string; trend: string;
  }>;
  top_degrading: Array<{ equipment_name: string; component: string; score: number; degradation_rate: number }>;
}

export interface RULItem {
  equipment_id: number; component: string; predicted_hours: number;
  ci_lo: number; ci_hi: number; degradation_model: string;
}

export interface DiagnosisResult {
  rank: number; failure_mode: string; fmea_id: number; confidence: number; severity: number;
}

export interface FMEARecord {
  id: number; equipment_type: string; component: string; failure_mode: string;
  severity: number; occurrence: number; detection: number; rpn: number;
  mitigation: string; symptoms: Record<string, unknown>;
}

export const healthApi = {
  getDashboard: (plantId: number) =>
    apiClient.get(`/api/health/dashboard?plant_id=${plantId}`) as Promise<HealthOverview>,

  getEquipmentDetail: (equipmentId: number) =>
    apiClient.get(`/api/health/equipment/${equipmentId}`),

  getRUL: (plantId?: number, equipmentId?: number) => {
    const params = new URLSearchParams();
    if (plantId) params.set('plant_id', String(plantId));
    if (equipmentId) params.set('equipment_id', String(equipmentId));
    return apiClient.get(`/api/health/rul?${params}`) as Promise<{ items: RULItem[] }>;
  },

  computeRUL: (equipmentId: number, component: string) =>
    apiClient.post(`/api/health/rul/compute?equipment_id=${equipmentId}&component=${component}`),

  getDiagnosis: (equipmentId: number) =>
    apiClient.get(`/api/health/diagnosis?equipment_id=${equipmentId}`),

  runDiagnosis: (equipmentId: number) =>
    apiClient.post(`/api/health/diagnosis/run?equipment_id=${equipmentId}`) as Promise<{ diagnoses: DiagnosisResult[] }>,

  searchFMEA: (equipmentType?: string, component?: string, q?: string) => {
    const params = new URLSearchParams();
    if (equipmentType) params.set('equipment_type', equipmentType);
    if (component) params.set('component', component);
    if (q) params.set('q', q);
    return apiClient.get(`/api/health/fmea?${params}`) as Promise<{ items: FMEARecord[] }>;
  },

  createFMEA: (data: Partial<FMEARecord>) =>
    apiClient.post('/api/health/fmea', data),

  getVibration: (equipmentId: number) =>
    apiClient.get(`/api/health/vibration?equipment_id=${equipmentId}`),

  getOilAnalysis: (equipmentId: number) =>
    apiClient.get(`/api/health/oil?equipment_id=${equipmentId}`),

  getValidation: () =>
    apiClient.get('/api/health/validation'),
};
