import type { PlantEquipment, PipeSegment } from './store';
import { getPointDefs } from './types';

export interface ValidationIssue {
  type: 'error' | 'warning';
  tag: string;
  message: string;
  equipmentId?: string;
  pipeId?: string;
}

export function validateTopology(
  equipment: PlantEquipment[],
  pipeSegments: PipeSegment[],
): ValidationIssue[] {
  const issues: ValidationIssue[] = [];

  // 1. Orphan equipment — no pipe connections at all
  const connectedIds = new Set<string>();
  for (const ps of pipeSegments) {
    connectedIds.add(ps.from_equipment_id);
    connectedIds.add(ps.to_equipment_id);
  }
  for (const eq of equipment) {
    if (!connectedIds.has(eq.id)) {
      issues.push({
        type: 'warning',
        tag: '孤立设备',
        message: `${eq.name} 没有连接任何管道`,
        equipmentId: eq.id,
      });
    }
  }

  // 2. Broken pipe references — reference non-existent equipment
  const eqIds = new Set(equipment.map(e => e.id));
  for (const ps of pipeSegments) {
    if (!eqIds.has(ps.from_equipment_id)) {
      issues.push({
        type: 'error',
        tag: '破损管道',
        message: `管段引用了不存在的源设备: ${ps.from_equipment_id}`,
        pipeId: ps.id,
      });
    }
    if (!eqIds.has(ps.to_equipment_id)) {
      issues.push({
        type: 'error',
        tag: '破损管道',
        message: `管段引用了不存在的目标设备: ${ps.to_equipment_id}`,
        pipeId: ps.id,
      });
    }
  }

  // 3. Invalid point codes
  for (const ps of pipeSegments) {
    const fromEq = equipment.find(e => e.id === ps.from_equipment_id);
    const toEq = equipment.find(e => e.id === ps.to_equipment_id);
    if (fromEq) {
      const points = getPointDefs(fromEq.type_code);
      if (points.length > 0 && !points.find(p => p.code === ps.from_point_code)) {
        issues.push({
          type: 'error',
          tag: '无效点位',
          message: `管段源点位 "${ps.from_point_code}" 在 ${fromEq.name} 上不存在`,
          pipeId: ps.id,
          equipmentId: fromEq.id,
        });
      }
    }
    if (toEq) {
      const points = getPointDefs(toEq.type_code);
      if (points.length > 0 && !points.find(p => p.code === ps.to_point_code)) {
        issues.push({
          type: 'error',
          tag: '无效点位',
          message: `管段目标点位 "${ps.to_point_code}" 在 ${toEq.name} 上不存在`,
          pipeId: ps.id,
          equipmentId: toEq.id,
        });
      }
    }
  }

  return issues;
}
