export interface EquipmentTraits {
  type_code: string;
  label: string;
  color: string;
  dimensions: { width: number; height: number; depth: number };
}

export interface PointDef {
  code: string;
  name: string;
  unit: string;
  data_type: 'float' | 'string';
  io_direction: 'input' | 'output' | 'calc';
  required?: boolean;
  sort_order?: number;
}

const EQUIPMENT_TRAITS: Record<string, EquipmentTraits> = {
  centrifugal_chiller: {
    type_code: 'centrifugal_chiller',
    label: '离心式冷水主机',
    color: '#3b82f6',
    dimensions: { width: 4, height: 2, depth: 2 },
  },
  pump: {
    type_code: 'pump',
    label: '水泵',
    color: '#22c55e',
    dimensions: { width: 1.5, height: 1, depth: 1 },
  },
  cooling_tower: {
    type_code: 'cooling_tower',
    label: '冷却塔',
    color: '#f97316',
    dimensions: { width: 3, height: 3, depth: 3 },
  },
  control_valve: {
    type_code: 'control_valve',
    label: '电动调节阀',
    color: '#eab308',
    dimensions: { width: 0.5, height: 0.3, depth: 0.8 },
  },
  temperature_sensor: {
    type_code: 'temperature_sensor',
    label: '温度传感器',
    color: '#94a3b8',
    dimensions: { width: 0.15, height: 0.15, depth: 0.15 },
  },
  pressure_sensor: {
    type_code: 'pressure_sensor',
    label: '压力传感器',
    color: '#94a3b8',
    dimensions: { width: 0.15, height: 0.15, depth: 0.15 },
  },
  flow_sensor: {
    type_code: 'flow_sensor',
    label: '流量计',
    color: '#94a3b8',
    dimensions: { width: 0.2, height: 0.15, depth: 0.3 },
  },
  power_meter: {
    type_code: 'power_meter',
    label: '功率计',
    color: '#94a3b8',
    dimensions: { width: 0.2, height: 0.15, depth: 0.2 },
  },
};

const POINT_DEFS: Record<string, PointDef[]> = {
  centrifugal_chiller: [
    { code: 'chw_supply_temp', name: '冷冻水供水温度', unit: '°C', data_type: 'float', io_direction: 'input', required: true, sort_order: 1 },
    { code: 'chw_return_temp', name: '冷冻水回水温度', unit: '°C', data_type: 'float', io_direction: 'input', required: true, sort_order: 2 },
    { code: 'cw_entering_temp', name: '冷却水进水温度', unit: '°C', data_type: 'float', io_direction: 'input', required: true, sort_order: 3 },
    { code: 'cw_leaving_temp', name: '冷却水出水温度', unit: '°C', data_type: 'float', io_direction: 'calc', required: true, sort_order: 4 },
    { code: 'power_kw', name: '实时功率', unit: 'kW', data_type: 'float', io_direction: 'calc', required: true, sort_order: 5 },
    { code: 'current_load_rt', name: '实时冷负荷', unit: 'RT', data_type: 'float', io_direction: 'calc', required: true, sort_order: 6 },
    { code: 'evap_flow_rate', name: '蒸发器流量', unit: 'L/s', data_type: 'float', io_direction: 'output', sort_order: 7 },
    { code: 'cond_flow_rate', name: '冷凝器流量', unit: 'L/s', data_type: 'float', io_direction: 'output', sort_order: 8 },
    { code: 'run_status', name: '运行状态', unit: 'enum', data_type: 'string', io_direction: 'output', required: true, sort_order: 9 },
    { code: 'cumulative_hours', name: '累计运行小时', unit: 'h', data_type: 'float', io_direction: 'output', sort_order: 10 },
  ],
  pump: [
    { code: 'speed_hz', name: '运行频率', unit: 'Hz', data_type: 'float', io_direction: 'input', required: true, sort_order: 1 },
    { code: 'power_kw', name: '实时功率', unit: 'kW', data_type: 'float', io_direction: 'calc', required: true, sort_order: 2 },
    { code: 'flow_lps', name: '流量', unit: 'L/s', data_type: 'float', io_direction: 'calc', required: true, sort_order: 3 },
    { code: 'inlet_pressure', name: '进口压力', unit: 'kPa', data_type: 'float', io_direction: 'input', sort_order: 4 },
    { code: 'outlet_pressure', name: '出口压力', unit: 'kPa', data_type: 'float', io_direction: 'calc', sort_order: 5 },
    { code: 'run_status', name: '运行状态', unit: 'enum', data_type: 'string', io_direction: 'output', required: true, sort_order: 6 },
  ],
  cooling_tower: [
    { code: 'fan_speed_hz', name: '风机频率', unit: 'Hz', data_type: 'float', io_direction: 'input', required: true, sort_order: 1 },
    { code: 'water_in_temp', name: '进水温度', unit: '°C', data_type: 'float', io_direction: 'input', required: true, sort_order: 2 },
    { code: 'water_out_temp', name: '出水温度', unit: '°C', data_type: 'float', io_direction: 'calc', required: true, sort_order: 3 },
    { code: 'water_flow_lps', name: '水流量', unit: 'L/s', data_type: 'float', io_direction: 'input', sort_order: 4 },
    { code: 'fan_power_kw', name: '风机功率', unit: 'kW', data_type: 'float', io_direction: 'calc', sort_order: 5 },
    { code: 'run_status', name: '运行状态', unit: 'enum', data_type: 'string', io_direction: 'output', required: true, sort_order: 6 },
  ],
  control_valve: [
    { code: 'valve_position', name: '阀门开度', unit: '%', data_type: 'float', io_direction: 'input', required: true, sort_order: 1 },
    { code: 'inlet_pressure', name: '阀前压力', unit: 'kPa', data_type: 'float', io_direction: 'input', required: true, sort_order: 2 },
    { code: 'outlet_pressure', name: '阀后压力', unit: 'kPa', data_type: 'float', io_direction: 'calc', required: true, sort_order: 3 },
    { code: 'flow_rate', name: '通过流量', unit: 'L/s', data_type: 'float', io_direction: 'calc', sort_order: 4 },
    { code: 'actuator_status', name: '执行器状态', unit: 'enum', data_type: 'string', io_direction: 'output', sort_order: 5 },
  ],
  temperature_sensor: [
    { code: 'measured_temp', name: '测量温度', unit: '°C', data_type: 'float', io_direction: 'output', required: true, sort_order: 1 },
  ],
  pressure_sensor: [
    { code: 'measured_pressure', name: '测量压力', unit: 'kPa', data_type: 'float', io_direction: 'output', required: true, sort_order: 1 },
  ],
  flow_sensor: [
    { code: 'measured_flow', name: '测量流量', unit: 'L/s', data_type: 'float', io_direction: 'output', required: true, sort_order: 1 },
  ],
  power_meter: [
    { code: 'measured_power', name: '测量功率', unit: 'kW', data_type: 'float', io_direction: 'output', required: true, sort_order: 1 },
  ],
};

export const POINT_COLORS: Record<'input' | 'output' | 'calc', string> = {
  input: '#ef4444',
  output: '#22d3ee',
  calc: '#22d3ee',
};

export function getEquipmentTraits(typeCode: string): EquipmentTraits {
  const traits = EQUIPMENT_TRAITS[typeCode];
  if (!traits) throw new Error(`Unknown equipment type: ${typeCode}`);
  return traits;
}

export function getPointDefs(typeCode: string): PointDef[] {
  return POINT_DEFS[typeCode] ?? [];
}

export function getDisplayPoints(typeCode: string): PointDef[] {
  return getPointDefs(typeCode).filter(p => p.io_direction === 'output' || p.io_direction === 'calc');
}

export function getControlPoints(typeCode: string): PointDef[] {
  return getPointDefs(typeCode).filter(p => p.io_direction === 'input');
}

export function getAllTypeCodes(): string[] {
  return Object.keys(EQUIPMENT_TRAITS);
}
