import { describe, it, expect } from 'vitest';
import { validateTopology } from '../../src/plant/validateTopology';
import type { PlantEquipment, PipeSegment } from '../../src/plant/store';

function makeEq(overrides: Partial<PlantEquipment> = {}): PlantEquipment {
  return {
    id: 'eq-1',
    name: 'test',
    type_code: 'centrifugal_chiller',
    position: { x: 0, y: 0, z: 0 },
    design_params: {},
    ...overrides,
  };
}

function makePipe(overrides: Partial<PipeSegment> = {}): PipeSegment {
  return {
    id: 'pipe-1',
    from_equipment_id: 'eq-1',
    from_point_code: 'chw_supply_temp',
    to_equipment_id: 'eq-2',
    to_point_code: 'outlet_pressure',
    diameter_mm: 200,
    length_m: 6,
    waypoints: [],
    ...overrides,
  };
}

describe('validateTopology', () => {
  it('returns no issues for empty equipment and pipes', () => {
    expect(validateTopology([], [])).toEqual([]);
  });

  it('returns no issues for valid topology', () => {
    const equipment = [
      makeEq({ id: 'ch-1', name: '冷水机组', type_code: 'centrifugal_chiller' }),
      makeEq({ id: 'p-1', name: '水泵', type_code: 'pump' }),
    ];
    const pipes = [
      makePipe({
        id: 'pipe-1',
        from_equipment_id: 'p-1',
        from_point_code: 'outlet_pressure',
        to_equipment_id: 'ch-1',
        to_point_code: 'chw_supply_temp',
      }),
    ];
    expect(validateTopology(equipment, pipes)).toEqual([]);
  });

  it('flags orphan equipment with no connections', () => {
    const equipment = [
      makeEq({ id: 'ch-1', name: '冷水机组' }),
      makeEq({ id: 'orphan', name: '孤立设备' }),
    ];
    const issues = validateTopology(equipment, []);
    expect(issues).toHaveLength(2);
    expect(issues.filter(i => i.tag === '孤立设备')).toHaveLength(2);
  });

  it('flags broken pipe reference to non-existent source equipment', () => {
    const equipment = [makeEq({ id: 'ch-1' })];
    const pipes = [makePipe({ from_equipment_id: 'ghost' })];
    const issues = validateTopology(equipment, pipes);
    expect(issues).toHaveLength(3);
    expect(issues.some(i => i.tag === '破损管道' && i.pipeId === 'pipe-1')).toBe(true);
  });

  it('flags broken pipe reference to non-existent target equipment', () => {
    const equipment = [makeEq({ id: 'ch-1' })];
    const pipes = [makePipe({ to_equipment_id: 'ghost' })];
    const issues = validateTopology(equipment, pipes);
    expect(issues.some(i => i.tag === '破损管道')).toBe(true);
  });

  it('flags invalid from_point_code', () => {
    const equipment = [
      makeEq({ id: 'ch-1', type_code: 'centrifugal_chiller' }),
      makeEq({ id: 'p-1', type_code: 'pump' }),
    ];
    const pipes = [makePipe({
      from_equipment_id: 'p-1',
      from_point_code: 'nonexistent_point',
      to_equipment_id: 'ch-1',
      to_point_code: 'chw_supply_temp',
    })];
    const issues = validateTopology(equipment, pipes);
    expect(issues.some(i => i.tag === '无效点位')).toBe(true);
  });

  it('flags invalid to_point_code', () => {
    const equipment = [
      makeEq({ id: 'ch-1', type_code: 'centrifugal_chiller' }),
      makeEq({ id: 'p-1', type_code: 'pump' }),
    ];
    const pipes = [makePipe({
      from_equipment_id: 'p-1',
      from_point_code: 'outlet_pressure',
      to_equipment_id: 'ch-1',
      to_point_code: 'nonexistent_point',
    })];
    const issues = validateTopology(equipment, pipes);
    expect(issues.some(i => i.tag === '无效点位')).toBe(true);
  });

  it('skips point code check for unknown equipment type', () => {
    const equipment = [
      makeEq({ id: 'unknown-1', type_code: 'unknown_type' }),
      makeEq({ id: 'unknown-2', type_code: 'unknown_type' }),
    ];
    const pipes = [makePipe({
      from_equipment_id: 'unknown-1',
      from_point_code: 'anything',
      to_equipment_id: 'unknown-2',
      to_point_code: 'anything',
    })];
    const issues = validateTopology(equipment, pipes);
    expect(issues.filter(i => i.tag === '无效点位')).toHaveLength(0);
  });

  it('tags errors and warnings correctly', () => {
    const equipment = [
      makeEq({ id: 'ch-1', type_code: 'centrifugal_chiller' }),
      makeEq({ id: 'orphan', name: '孤立' }),
    ];
    const pipes = [makePipe({
      from_equipment_id: 'ghost',
      to_equipment_id: 'ch-1',
      to_point_code: 'chw_supply_temp',
    })];
    const issues = validateTopology(equipment, pipes);
    const errors = issues.filter(i => i.type === 'error');
    const warnings = issues.filter(i => i.type === 'warning');
    expect(errors.length).toBeGreaterThan(0);
    expect(warnings.length).toBeGreaterThan(0);
  });

  it('includes equipmentId and pipeId for navigation', () => {
    const equipment = [makeEq({ id: 'ch-1', name: '冷水机组' })];
    const issues = validateTopology(equipment, []);
    expect(issues[0].equipmentId).toBe('ch-1');
    expect(issues[0].pipeId).toBeUndefined();
  });
});
