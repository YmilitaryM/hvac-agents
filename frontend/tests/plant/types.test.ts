import { describe, it, expect } from 'vitest';
import {
  getEquipmentTraits,
  getPointDefs,
  getDisplayPoints,
  getControlPoints,
  getAllTypeCodes,
  POINT_COLORS,
} from '../../src/plant/types';

describe('Equipment types', () => {
  it('centrifugal_chiller has correct traits', () => {
    const traits = getEquipmentTraits('centrifugal_chiller');
    expect(traits.label).toBe('离心式冷水主机');
    expect(traits.color).toBe('#3b82f6');
    expect(traits.dimensions).toEqual({ width: 4, height: 2, depth: 2 });
  });

  it('pump has correct traits', () => {
    const traits = getEquipmentTraits('pump');
    expect(traits.label).toBe('水泵');
    expect(traits.color).toBe('#22c55e');
  });

  it('cooling_tower has correct traits', () => {
    const traits = getEquipmentTraits('cooling_tower');
    expect(traits.label).toBe('冷却塔');
    expect(traits.color).toBe('#f97316');
  });

  it('control_valve has correct traits', () => {
    const traits = getEquipmentTraits('control_valve');
    expect(traits.label).toBe('电动调节阀');
    expect(traits.color).toBe('#eab308');
  });

  it('throws for unknown type', () => {
    expect(() => getEquipmentTraits('unknown_type')).toThrow('Unknown equipment type');
  });
});

describe('getAllTypeCodes', () => {
  it('returns all equipment type codes', () => {
    const codes = getAllTypeCodes();
    expect(codes).toHaveLength(8);
    expect(codes).toContain('centrifugal_chiller');
    expect(codes).toContain('pump');
    expect(codes).toContain('cooling_tower');
    expect(codes).toContain('control_valve');
    expect(codes).toContain('temperature_sensor');
    expect(codes).toContain('pressure_sensor');
    expect(codes).toContain('flow_sensor');
    expect(codes).toContain('power_meter');
  });
});

describe('getPointDefs', () => {
  it('returns point definitions for a known type', () => {
    const points = getPointDefs('centrifugal_chiller');
    expect(points).toHaveLength(10);
    expect(points[0]).toMatchObject({
      code: 'chw_supply_temp',
      name: '冷冻水供水温度',
      io_direction: 'input',
    });
  });

  it('returns point definitions for pump', () => {
    const points = getPointDefs('pump');
    expect(points).toHaveLength(6);
  });

  it('returns empty array for unknown type', () => {
    const points = getPointDefs('unknown_type');
    expect(points).toEqual([]);
  });
});

describe('Point helpers', () => {
  it('getDisplayPoints returns output and calc points for centrifugal_chiller', () => {
    const points = getDisplayPoints('centrifugal_chiller');
    expect(points).toHaveLength(7);
    expect(points.every(p => p.io_direction === 'output' || p.io_direction === 'calc')).toBe(true);
  });

  it('getControlPoints returns input points for centrifugal_chiller', () => {
    const points = getControlPoints('centrifugal_chiller');
    expect(points).toHaveLength(3);
    expect(points.every(p => p.io_direction === 'input')).toBe(true);
  });

  it('getDisplayPoints returns output and calc points for pump', () => {
    const points = getDisplayPoints('pump');
    expect(points).toHaveLength(4);
    expect(points.every(p => p.io_direction === 'output' || p.io_direction === 'calc')).toBe(true);
  });

  it('getControlPoints returns input points for pump', () => {
    const points = getControlPoints('pump');
    expect(points).toHaveLength(2);
    expect(points.every(p => p.io_direction === 'input')).toBe(true);
  });

  it('POINT_COLORS maps directions', () => {
    expect(POINT_COLORS.input).toBe('#ef4444');
    expect(POINT_COLORS.output).toBe('#22d3ee');
    expect(POINT_COLORS.calc).toBe('#22d3ee');
  });
});
