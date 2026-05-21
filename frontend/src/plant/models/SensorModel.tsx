import { getEquipmentTraits } from '../types';

interface SensorModelProps {
  position: [number, number, number];
  onClick?: () => void;
  selected?: boolean;
  typeCode: string;
}

export function SensorModel({ position, onClick, selected, typeCode }: SensorModelProps) {
  const { color, dimensions } = getEquipmentTraits(typeCode);
  const { width, height, depth } = dimensions;

  return (
    <group position={position} onClick={onClick}>
      {/* Body */}
      <mesh castShadow>
        <boxGeometry args={[width, height, depth]} />
        <meshStandardMaterial color={color} metalness={0.5} roughness={0.3} />
      </mesh>
      {/* Probe / antenna */}
      <mesh castShadow position={[0, height * 0.6, 0]}>
        <cylinderGeometry args={[width * 0.2, width * 0.2, height * 0.6, 8]} />
        <meshStandardMaterial color="#64748b" metalness={0.8} roughness={0.2} />
      </mesh>
      {/* Selection highlight */}
      {selected && (
        <mesh>
          <boxGeometry args={[width + 0.2, height + 0.2, depth + 0.2]} />
          <meshBasicMaterial color="#38bdf8" wireframe />
        </mesh>
      )}
    </group>
  );
}
