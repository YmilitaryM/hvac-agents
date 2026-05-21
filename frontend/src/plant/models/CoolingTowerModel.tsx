import * as THREE from 'three';
import { getEquipmentTraits } from '../types';

interface CoolingTowerModelProps {
  position: [number, number, number];
  onClick?: () => void;
  selected?: boolean;
}

export function CoolingTowerModel({ position, onClick, selected }: CoolingTowerModelProps) {
  const { color, dimensions } = getEquipmentTraits('cooling_tower');
  const { width, height, depth } = dimensions;

  return (
    <group position={position} onClick={onClick}>
      {/* Tower body */}
      <mesh castShadow position={[0, height * 0.6, 0]}>
        <boxGeometry args={[width, height * 0.8, depth]} />
        <meshStandardMaterial color={color} metalness={0.1} roughness={0.7} />
      </mesh>
      {/* Fan deck on top */}
      <mesh castShadow position={[0, height, 0]}>
        <cylinderGeometry args={[width * 0.3, width * 0.35, 0.3, 16]} />
        <meshStandardMaterial color="#64748b" metalness={0.4} roughness={0.4} />
      </mesh>
      {/* Fan grill */}
      <mesh position={[0, height + 0.15, 0]}>
        <ringGeometry args={[0.1, width * 0.28, 32]} />
        <meshBasicMaterial color="#475569" side={THREE.DoubleSide} />
      </mesh>
      {selected && (
        <mesh position={[0, height / 2, 0]}>
          <boxGeometry args={[width + 0.2, height + 0.2, depth + 0.2]} />
          <meshBasicMaterial color="#38bdf8" wireframe />
        </mesh>
      )}
    </group>
  );
}
