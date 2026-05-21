import { useState, useCallback } from 'react';
import { usePlantStore, type Position3D } from '../store';
import { computePipePath, computePipeLength } from '../pipePath';

interface ConnectionState {
  fromEquipmentId: string;
  fromPointCode: string;
  startPos: Position3D;
}

export function usePipeConnection() {
  const [activeConnection, setActiveConnection] = useState<ConnectionState | null>(null);
  const addPipeSegment = usePlantStore(s => s.addPipeSegment);
  const equipment = usePlantStore(s => s.equipment);

  const startConnection = useCallback((equipmentId: string, pointCode: string) => {
    const eq = equipment.find(e => e.id === equipmentId);
    if (!eq) return;
    setActiveConnection({
      fromEquipmentId: equipmentId,
      fromPointCode: pointCode,
      startPos: { ...eq.position },
    });
  }, [equipment]);

  const completeConnection = useCallback((toEquipmentId: string, toPointCode: string) => {
    if (!activeConnection) return;
    if (activeConnection.fromEquipmentId === toEquipmentId) {
      setActiveConnection(null);
      return;
    }
    const toEq = equipment.find(e => e.id === toEquipmentId);
    if (!toEq) { setActiveConnection(null); return; }

    const waypoints = computePipePath(activeConnection.startPos, toEq.position);
    const length = computePipeLength(activeConnection.startPos, toEq.position, waypoints);

    addPipeSegment({
      id: `pipe-${Date.now()}`,
      from_equipment_id: activeConnection.fromEquipmentId,
      from_point_code: activeConnection.fromPointCode,
      to_equipment_id: toEquipmentId,
      to_point_code: toPointCode,
      diameter_mm: 200,
      length_m: length,
      waypoints,
    });
    setActiveConnection(null);
  }, [activeConnection, equipment, addPipeSegment]);

  const cancelConnection = useCallback(() => {
    setActiveConnection(null);
  }, []);

  return { activeConnection, startConnection, completeConnection, cancelConnection };
}
