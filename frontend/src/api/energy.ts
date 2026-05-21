import { apiClient } from './client';

export interface EnergyDashboard {
  plant_id: number;
  current_cop: number;
  total_power_kw: number;
  cooling_load_rt: number;
  electricity_cost_per_hour: number;
  outdoor_wb_temp: number;
  trend: { cop: number[]; power_kw: number[]; load_rt: number[] };
  equipment_breakdown: { chillers: number; pumps: number; cooling_towers: number };
}

export interface EnergyBaseline {
  plant_id: number;
  current_baseline: { baseline_kwh_per_rt: number; method: string; r_squared: number; climate_zone: string };
  standards_comparison: { gb50189_scop_target: number; current_scop: number; compliant: boolean; gb19577_grade: number };
}

export interface DemandData {
  plant_id: number;
  current_kw: number;
  predicted_peak_kw: number;
  demand_limit_kw: number;
  warning: boolean;
  trend: number[];
  events: Array<{ id: number; start_time: string; peak_kw: number; strategy: string; actual_reduction_kw: number }>;
}

export interface MVResult {
  baseline_energy_kwh: number;
  actual_energy_kwh: number;
  savings_kwh: number;
  savings_pct: number;
  uncertainty_pct: number;
  cv_rmse_pct: number;
  nmbe_pct: number;
  compliant_ashrae_g14: boolean;
  compliant_gb28750: boolean;
  coal_equivalent_tons: number;
  carbon_reduction_kg: number;
}

export interface EnergyComparison {
  period: string;
  current: { total_kwh: number; avg_cop: number; avg_power_kw: number };
  previous: { total_kwh: number; avg_cop: number; avg_power_kw: number };
  mom_change_pct: { total_kwh: number; avg_cop: number; avg_power_kw: number };
  yoy_change_pct: { total_kwh: number; avg_cop: number; avg_power_kw: number };
}

export const energyApi = {
  getDashboard: (plantId: number) =>
    apiClient.get(`/api/energy/dashboard?plant_id=${plantId}`) as Promise<EnergyDashboard>,

  getBreakdown: (plantId: number) =>
    apiClient.get(`/api/energy/breakdown?plant_id=${plantId}`),

  getBaseline: (plantId: number) =>
    apiClient.get(`/api/energy/baseline?plant_id=${plantId}`) as Promise<EnergyBaseline>,

  getDemand: (plantId: number) =>
    apiClient.get(`/api/energy/peak-demand?plant_id=${plantId}`) as Promise<DemandData>,

  getMv: (plantId: number) =>
    apiClient.get(`/api/energy/mv/verify?plant_id=${plantId}`) as Promise<MVResult>,

  getComparison: (plantId: number, period: string = 'month') =>
    apiClient.get(`/api/energy/comparison?plant_id=${plantId}&period=${period}`) as Promise<EnergyComparison>,

  getReports: (plantId: number, period?: string) =>
    apiClient.get(`/api/energy/reports?plant_id=${plantId}${period ? `&period=${period}` : ''}`),

  generateReport: (plantId: number, period: string, reportType: string) =>
    apiClient.post(`/api/energy/reports/generate?plant_id=${plantId}&period=${period}&report_type=${reportType}`),

  optimizeDemand: (plantId: number) =>
    apiClient.post(`/api/energy/peak-demand/optimize?plant_id=${plantId}`),

  getPowerQuality: (equipmentId: number) =>
    apiClient.get(`/api/energy/power-quality?equipment_id=${equipmentId}`),
};
