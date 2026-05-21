import { describe, it, expect } from 'vitest';
import { computeLayout } from '../../src/plant/autoLayout';

describe('computeLayout', () => {
  it('arranges chillers in a row, pumps after, towers after', () => {
    const equipment = [
      { id: 'ch-1', type_code: 'centrifugal_chiller' },
      { id: 'ch-2', type_code: 'centrifugal_chiller' },
      { id: 'p-1', type_code: 'pump' },
      { id: 'ct-1', type_code: 'cooling_tower' },
    ];
    const positions = computeLayout(equipment);
    expect(positions).toHaveLength(4);
    // Chillers at z=0 plane
    expect(positions[0].z).toBe(0);
    expect(positions[1].z).toBe(0);
    expect(positions[0].x).toBeLessThan(positions[1].x);
    // Pumps at z > 0
    expect(positions[2].z).toBeGreaterThan(0);
    // Towers are furthest
    expect(positions[3].z).toBeGreaterThan(positions[2].z);
  });

  it('returns empty array for empty input', () => {
    expect(computeLayout([])).toHaveLength(0);
  });
});
