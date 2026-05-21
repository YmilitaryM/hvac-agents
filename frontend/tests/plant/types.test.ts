import { describe, it, expect } from 'vitest';
import {
  getEquipmentTraits,
  getDisplayPoints,
  getControlPoints,
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

describe('Point helpers', () => {
  it('getDisplayPoints returns output and calc points', () => {
    const points = getDisplayPoints('centrifugal_chiller');
    expect(points.length).toBeGreaterThan(0);
    expect(points.every(p => p.io_direction === 'output' || p.io_direction === 'calc')).toBe(true);
  });

  it('getControlPoints returns input points', () => {
    const points = getControlPoints('centrifugal_chiller');
    expect(points.length).toBeGreaterThan(0);
    expect(points.every(p => p.io_direction === 'input')).toBe(true);
  });

  it('POINT_COLORS maps directions', () => {
    expect(POINT_COLORS.input).toBe('#ef4444');
    expect(POINT_COLORS.output).toBe('#22d3ee');
    expect(POINT_COLORS.calc).toBe('#22d3ee');
  });
});
