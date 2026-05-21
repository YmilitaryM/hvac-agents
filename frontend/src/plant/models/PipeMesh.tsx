import * as THREE from 'three';
import { useMemo } from 'react';
import type { Position3D } from '../store';

interface PipeMeshProps {
  start: Position3D;
  end: Position3D;
  waypoints: Position3D[];
  diameter: number; // mm
  color?: string;
  onClick?: () => void;
  selected?: boolean;
}

export function PipeMesh({ start, end, waypoints, diameter, color = '#64748b', onClick, selected }: PipeMeshProps) {
  const radius = (diameter / 1000) / 2; // mm to m radius

  const path = useMemo(() => {
    const points: THREE.Vector3[] = [];
    points.push(new THREE.Vector3(start.x, start.y, start.z));
    for (const wp of waypoints) {
      points.push(new THREE.Vector3(wp.x, wp.y, wp.z));
    }
    points.push(new THREE.Vector3(end.x, end.y, end.z));
    return new THREE.CatmullRomCurve3(points, false, 'catmullrom', 0);
  }, [start, end, waypoints]);

  return (
    <mesh onClick={onClick}>
      <tubeGeometry args={[path, 16, Math.max(radius, 0.05), 8, false]} />
      <meshStandardMaterial color={selected ? '#38bdf8' : color} metalness={0.7} roughness={0.3} />
    </mesh>
  );
}
