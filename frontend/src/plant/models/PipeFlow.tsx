import { useRef, useMemo } from 'react';
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';
import type { Position3D } from '../store';

interface PipeFlowProps {
  start: Position3D;
  end: Position3D;
  waypoints: Position3D[];
  diameter: number;
  flowSpeed?: number;
}

function buildCurve(start: Position3D, end: Position3D, waypoints: Position3D[]): THREE.CatmullRomCurve3 {
  const points = [new THREE.Vector3(start.x, start.y, start.z)];
  for (const wp of waypoints) {
    points.push(new THREE.Vector3(wp.x, wp.y, wp.z));
  }
  points.push(new THREE.Vector3(end.x, end.y, end.z));
  return new THREE.CatmullRomCurve3(points, false, 'catmullrom', 0);
}

export function PipeFlow({ start, end, waypoints, diameter, flowSpeed = 1.5 }: PipeFlowProps) {
  const curve = useMemo(() => buildCurve(start, end, waypoints), [start, end, waypoints]);
  const pathLength = useMemo(() => curve.getLength(), [curve]);

  const particleCount = useMemo(() => Math.max(3, Math.min(20, Math.round(pathLength))), [pathLength]);
  const tRef = useRef(new Float32Array(particleCount));
  const groupRef = useRef<THREE.Group>(null!);

  // Initialize particle t values spread evenly along the curve
  const initialized = useRef(false);
  if (!initialized.current) {
    for (let i = 0; i < particleCount; i++) {
      tRef.current[i] = i / particleCount;
    }
    initialized.current = true;
  }

  useFrame((_, delta) => {
    if (!groupRef.current) return;
    const dt = (flowSpeed * delta) / pathLength;
    const children = groupRef.current.children;

    for (let i = 0; i < particleCount; i++) {
      let t = tRef.current[i] + dt;
      if (t >= 1) t -= 1;
      tRef.current[i] = t;

      const pt = curve.getPointAt(t);
      children[i].position.set(pt.x, pt.y, pt.z);
    }
  });

  const particleSize = Math.max(0.04, (diameter / 1000) * 0.3);

  return (
    <group ref={groupRef}>
      {Array.from({ length: particleCount }).map((_, i) => (
        <mesh key={i}>
          <sphereGeometry args={[particleSize, 6, 6]} />
          <meshStandardMaterial
            color="#22d3ee"
            emissive="#22d3ee"
            emissiveIntensity={1.2}
            transparent
            opacity={0.85}
          />
        </mesh>
      ))}
    </group>
  );
}
