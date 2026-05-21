import * as THREE from 'three';
import { getEquipmentTraits } from '../types';

interface ValveModelProps {
  position: [number, number, number];
  onClick?: () => void;
  selected?: boolean;
}

export function ValveModel({ position, onClick, selected }: ValveModelProps) {
  const { color, dimensions } = getEquipmentTraits('control_valve');
  const { width, height, depth } = dimensions;

  return (
    <group position={position} onClick={onClick}>
      {/* Pipe section */}
      <mesh castShadow rotation={[0, 0, Math.PI / 2]}>
        <cylinderGeometry args={[0.15, 0.15, width, 8]} />
        <meshStandardMaterial color="#94a3b8" metalness={0.8} roughness={0.3} />
      </mesh>
      {/* Actuator box on top */}
      <mesh castShadow position={[0, height * 0.6, 0]}>
        <boxGeometry args={[width * 0.5, height * 0.8, depth * 0.6]} />
        <meshStandardMaterial color={color} metalness={0.4} roughness={0.4} />
      </mesh>
      {/* Handwheel */}
      <mesh position={[0, height * 0.6 + height * 0.4, 0]}>
        <torusGeometry args={[0.15, 0.03, 8, 16]} />
        <meshStandardMaterial color="#cbd5e1" metalness={0.9} roughness={0.2} />
      </mesh>
      {selected && (
        <mesh>
          <boxGeometry args={[width + 0.1, height + 0.1, depth + 0.1]} />
          <meshBasicMaterial color="#38bdf8" wireframe />
        </mesh>
      )}
    </group>
  );
}
