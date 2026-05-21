import * as THREE from 'three';
import { getEquipmentTraits } from '../types';

interface PumpModelProps {
  position: [number, number, number];
  onClick?: () => void;
  selected?: boolean;
}

export function PumpModel({ position, onClick, selected }: PumpModelProps) {
  const { color, dimensions } = getEquipmentTraits('pump');
  const { width, height, depth } = dimensions;

  return (
    <group position={position} onClick={onClick}>
      {/* Pump body (horizontal cylinder) */}
      <mesh castShadow rotation={[0, 0, Math.PI / 2]}>
        <cylinderGeometry args={[height * 0.35, height * 0.35, width * 0.6, 16]} />
        <meshStandardMaterial color={color} metalness={0.4} roughness={0.3} />
      </mesh>
      {/* Motor on top */}
      <mesh castShadow position={[0, height * 0.5, 0]}>
        <boxGeometry args={[width * 0.4, height * 0.4, depth * 0.4]} />
        <meshStandardMaterial color="#475569" metalness={0.6} roughness={0.3} />
      </mesh>
      {/* Flanges */}
      {[width * 0.3, -width * 0.3].map((fx, i) => (
        <mesh key={i} position={[fx, 0, 0]} rotation={[0, Math.PI / 2, 0]}>
          <torusGeometry args={[height * 0.3, 0.05, 8, 16]} />
          <meshStandardMaterial color="#94a3b8" metalness={0.8} roughness={0.2} />
        </mesh>
      ))}
      {selected && (
        <mesh>
          <boxGeometry args={[width + 0.2, height + 0.2, depth + 0.2]} />
          <meshBasicMaterial color="#38bdf8" wireframe />
        </mesh>
      )}
    </group>
  );
}
