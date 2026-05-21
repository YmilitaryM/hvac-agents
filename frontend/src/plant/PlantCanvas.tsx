import { useRef, useCallback, useMemo } from 'react';
import * as THREE from 'three';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Grid, TransformControls, Html } from '@react-three/drei';
import { usePlantStore } from './store';
import { ChillerModel, PumpModel, CoolingTowerModel, ValveModel, SensorModel, PipeMesh, PipeFlow } from './models';
import { getPointDefs, POINT_COLORS } from './types';
import { usePipeConnection } from './interaction/usePipeConnection';
import SensorOverlay from './SensorOverlay';

interface EquipmentNodeProps {
  eq: {
    id: string;
    name: string;
    type_code: string;
    position: { x: number; y: number; z: number };
  };
}

function EquipmentNode({ eq }: EquipmentNodeProps) {
  const selectedId = usePlantStore(s => s.selectedId);
  const setSelection = usePlantStore(s => s.setSelection);
  const pos: [number, number, number] = [eq.position.x, eq.position.y, eq.position.z];
  const selected = selectedId === eq.id;

  const props = { position: pos, onClick: () => setSelection(eq.id), selected };

  switch (eq.type_code) {
    case 'centrifugal_chiller': return <ChillerModel {...props} />;
    case 'pump': return <PumpModel {...props} />;
    case 'cooling_tower': return <CoolingTowerModel {...props} />;
    case 'control_valve': return <ValveModel {...props} />;
    case 'temperature_sensor':
    case 'pressure_sensor':
    case 'flow_sensor':
    case 'power_meter':
      return <SensorModel {...props} typeCode={eq.type_code} />;
    default: return <ChillerModel {...props} />;
  }
}

interface PointBadgesProps {
  eq: {
    id: string;
    type_code: string;
    position: { x: number; y: number; z: number };
  };
  onPointClick?: (pointCode: string) => void;
  activePointCode?: string | null;
}

function PointBadges({ eq, onPointClick, activePointCode }: PointBadgesProps) {
  const points = getPointDefs(eq.type_code);
  return (
    <group>
      {points.map((p, i) => {
        const angle = (i / points.length) * Math.PI * 2;
        const r = 1.2;
        const px = eq.position.x + Math.cos(angle) * r;
        const py = eq.position.y + 1 + (i % 3) * 0.3;
        const pz = eq.position.z + Math.sin(angle) * r;
        const baseColor = POINT_COLORS[p.io_direction] || '#ffffff';
        const isActive = activePointCode === p.code;
        const color = isActive ? '#fbbf24' : baseColor;
        const scale = isActive ? 1.5 : 1;
        return (
          <mesh
            key={p.code}
            position={[px, py, pz]}
            scale={scale}
            onClick={(e) => { e.stopPropagation(); onPointClick?.(p.code); }}
          >
            <sphereGeometry args={[0.1, 16, 16]} />
            <meshStandardMaterial
              color={color}
              emissive={color}
              emissiveIntensity={isActive ? 0.9 : 0.5}
            />
          </mesh>
        );
      })}
    </group>
  );
}

function PipeLines({ showFlow }: { showFlow: boolean }) {
  const pipeSegments = usePlantStore(s => s.pipeSegments);
  const equipment = usePlantStore(s => s.equipment);
  const selectedId = usePlantStore(s => s.selectedId);
  const setSelection = usePlantStore(s => s.setSelection);

  const eqMap = useMemo(() => {
    const m = new Map<string, typeof equipment[number]>();
    for (const eq of equipment) m.set(eq.id, eq);
    return m;
  }, [equipment]);

  return (
    <group>
      {pipeSegments.map(ps => {
        const fromEq = eqMap.get(ps.from_equipment_id);
        const toEq = eqMap.get(ps.to_equipment_id);
        if (!fromEq || !toEq) return null;
        return (
          <group key={ps.id}>
            <PipeMesh
              start={fromEq.position}
              end={toEq.position}
              waypoints={ps.waypoints}
              diameter={ps.diameter_mm}
              onClick={() => setSelection(ps.id)}
              selected={selectedId === ps.id}
            />
            {showFlow && (
              <PipeFlow
                start={fromEq.position}
                end={toEq.position}
                waypoints={ps.waypoints}
                diameter={ps.diameter_mm}
              />
            )}
          </group>
        );
      })}
    </group>
  );
}

function SelectedTransform() {
  const selectedId = usePlantStore(s => s.selectedId);
  const equipment = usePlantStore(s => s.equipment);
  const updatePosition = usePlantStore(s => s.updateEquipmentPosition);
  const meshRef = useRef<THREE.Mesh>(null!);

  const selected = equipment.find(e => e.id === selectedId);
  if (!selected) return null;

  const handleChange = useCallback(() => {
    if (meshRef.current) {
      const p = meshRef.current.position;
      updatePosition(selected.id, { x: p.x, y: p.y, z: p.z });
    }
  }, [selected.id, updatePosition]);

  return (
    <TransformControls
      object={meshRef}
      mode="translate"
      onObjectChange={handleChange}
    >
      <mesh ref={meshRef} position={[selected.position.x, selected.position.y, selected.position.z]} visible={false}>
        <boxGeometry args={[0.1, 0.1, 0.1]} />
      </mesh>
    </TransformControls>
  );
}

export default function PlantCanvas({ showFlow = true }: { showFlow?: boolean }) {
  const equipment = usePlantStore(s => s.equipment);
  const { activeConnection, startConnection, completeConnection } = usePipeConnection();

  const handlePointClick = useCallback((eqId: string, pointCode: string) => {
    if (!activeConnection) {
      startConnection(eqId, pointCode);
    } else {
      completeConnection(eqId, pointCode);
    }
  }, [activeConnection, startConnection, completeConnection]);

  return (
    <Canvas
      shadows
      camera={{ position: [15, 12, 15], fov: 50, near: 0.1, far: 200 }}
      style={{ width: '100%', height: '100%' }}
    >
      <ambientLight intensity={0.4} />
      <directionalLight
        position={[20, 30, 10]}
        intensity={0.8}
        castShadow
        shadow-mapSize-width={1024}
        shadow-mapSize-height={1024}
      />
      <Grid
        position={[0, -0.01, 0]}
        args={[40, 40]}
        cellSize={2}
        cellThickness={0.5}
        cellColor="#334155"
        sectionSize={10}
        sectionThickness={1}
        sectionColor="#1e293b"
        fadeDistance={50}
        infiniteGrid
      />
      <group>
        {equipment.map(eq => (
          <group key={eq.id}>
            <EquipmentNode eq={eq} />
            <PointBadges
              eq={eq}
              onPointClick={(pointCode) => handlePointClick(eq.id, pointCode)}
              activePointCode={
                activeConnection?.fromEquipmentId === eq.id
                  ? activeConnection.fromPointCode
                  : null
              }
            />
          </group>
        ))}
        <PipeLines showFlow={showFlow} />
      </group>
      <SelectedTransform />
      <OrbitControls
        makeDefault
        maxPolarAngle={Math.PI / 2.2}
        minDistance={5}
        maxDistance={60}
        target={[0, 1, 0]}
        touches={{
          ONE: THREE.TOUCH.ROTATE,
          TWO: THREE.TOUCH.DOLLY_PAN,
        }}
      />
      {activeConnection && (
        <Html position={[0, -1, 0]} center>
          <div className="bg-amber-500 text-black text-xs px-2 py-1 rounded whitespace-nowrap">
            连接中... 点击目标设备点位完成连接 (点击同一设备取消)
          </div>
        </Html>
      )}
      <SensorOverlay />
    </Canvas>
  );
}
