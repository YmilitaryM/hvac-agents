import type { Position3D } from './store';

interface LayoutInput {
  id: string;
  type_code: string;
}

const LAYOUT_ORDER = [
  'centrifugal_chiller',
  'pump',
  'cooling_tower',
  'control_valve',
  'temperature_sensor',
  'pressure_sensor',
  'flow_sensor',
  'power_meter',
];

const SPACING_X = 6;
const SPACING_Z = 8;

export function computeLayout(equipment: LayoutInput[]): Position3D[] {
  if (equipment.length === 0) return [];

  const positions: Position3D[] = [];
  const rowBaseZ: Record<string, number> = {};

  let currentZ = 0;
  for (const typeCode of LAYOUT_ORDER) {
    const items = equipment.filter(e => e.type_code === typeCode);
    if (items.length > 0) {
      rowBaseZ[typeCode] = currentZ;
      currentZ += SPACING_Z;
    }
  }

  for (const eq of equipment) {
    const typeIdx = LAYOUT_ORDER.indexOf(eq.type_code);
    if (typeIdx === -1) {
      positions.push({ x: 0, y: 0, z: 0 });
      continue;
    }
    const z = rowBaseZ[eq.type_code] ?? 0;
    const rowItems = equipment.filter(e => e.type_code === eq.type_code);
    const itemIdx = rowItems.indexOf(eq);
    const totalInRow = rowItems.length;
    const x = (itemIdx - (totalInRow - 1) / 2) * SPACING_X;
    positions.push({ x, y: 0, z });
  }

  return positions;
}
