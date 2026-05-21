import { Canvas } from '@react-three/fiber';
import { OrbitControls, Grid } from '@react-three/drei';
import { usePlantStore } from './store';
import { ChillerModel, PumpModel, CoolingTowerModel, ValveModel, PipeMesh } from './models';
import { getPointDefs, POINT_COLORS } from './types';

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
    default: return <ChillerModel {...props} />;
  }
}

interface PointBadgesProps {
  eq: {
    id: string;
    type_code: string;
    position: { x: number; y: number; z: number };
  };
}

function PointBadges({ eq }: PointBadgesProps) {
  const points = getPointDefs(eq.type_code);
  return (
    <group>
      {points.map((p, i) => {
        const angle = (i / points.length) * Math.PI * 2;
        const r = 1.2;
        const px = eq.position.x + Math.cos(angle) * r;
        const py = eq.position.y + 1 + (i % 3) * 0.3;
        const pz = eq.position.z + Math.sin(angle) * r;
        const color = POINT_COLORS[p.io_direction] || '#ffffff';
        return (
          <mesh key={p.code} position={[px, py, pz]}>
            <sphereGeometry args={[0.1, 16, 16]} />
            <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.5} />
          </mesh>
        );
      })}
    </group>
  );
}

function PipeLines() {
  const pipeSegments = usePlantStore(s => s.pipeSegments);
  const equipment = usePlantStore(s => s.equipment);
  const selectedId = usePlantStore(s => s.selectedId);
  const setSelection = usePlantStore(s => s.setSelection);

  return (
    <group>
      {pipeSegments.map(ps => {
        const fromEq = equipment.find(e => e.id === ps.from_equipment_id);
        const toEq = equipment.find(e => e.id === ps.to_equipment_id);
        if (!fromEq || !toEq) return null;
        return (
          <PipeMesh
            key={ps.id}
            start={fromEq.position}
            end={toEq.position}
            waypoints={ps.waypoints}
            diameter={ps.diameter_mm}
            onClick={() => setSelection(ps.id)}
            selected={selectedId === ps.id}
          />
        );
      })}
    </group>
  );
}

export default function PlantCanvas() {
  const equipment = usePlantStore(s => s.equipment);

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
            <PointBadges eq={eq} />
          </group>
        ))}
        <PipeLines />
      </group>
      <OrbitControls
        makeDefault
        maxPolarAngle={Math.PI / 2.2}
        minDistance={5}
        maxDistance={60}
        target={[0, 1, 0]}
      />
    </Canvas>
  );
}
