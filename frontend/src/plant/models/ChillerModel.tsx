import * as THREE from 'three';
import { useRef } from 'react';
import { getEquipmentTraits } from '../types';

interface ChillerModelProps {
  position: [number, number, number];
  onClick?: () => void;
  selected?: boolean;
}

export function ChillerModel({ position, onClick, selected }: ChillerModelProps) {
  const groupRef = useRef<THREE.Group>(null);
  const { color, dimensions } = getEquipmentTraits('centrifugal_chiller');
  const { width, height, depth } = dimensions;

  return (
    <group ref={groupRef} position={position} onClick={onClick}>
      {/* Main body */}
      <mesh castShadow position={[0, height / 2, 0]}>
        <boxGeometry args={[width, height, depth]} />
        <meshStandardMaterial color={color} metalness={0.3} roughness={0.5} />
      </mesh>
      {/* Motor cylinder on top */}
      <mesh castShadow position={[0, height + 0.3, 0]} rotation={[Math.PI / 2, 0, 0]}>
        <cylinderGeometry args={[0.3, 0.3, width * 0.6, 16]} />
        <meshStandardMaterial color="#64748b" metalness={0.6} roughness={0.3} />
      </mesh>
      {/* Nozzles: 4 pipe stubs on sides */}
      {[[-1, 0.3, 1], [1, 0.3, 1], [-1, 0.3, -1], [1, 0.3, -1]].map(([nx, ny_sign, nz], i) => (
        <mesh key={i} position={[nx * width / 2, ny_sign + height * 0.3, nz * depth / 2]}>
          <cylinderGeometry args={[0.15, 0.15, 0.5, 8]} />
          <meshStandardMaterial color="#94a3b8" metalness={0.8} roughness={0.2} />
        </mesh>
      ))}
      {/* Selection highlight */}
      {selected && (
        <mesh position={[0, height / 2, 0]}>
          <boxGeometry args={[width + 0.2, height + 0.2, depth + 0.2]} />
          <meshBasicMaterial color="#38bdf8" wireframe />
        </mesh>
      )}
    </group>
  );
}
