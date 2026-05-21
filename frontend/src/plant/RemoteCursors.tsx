import { useRef, useMemo } from 'react';
import * as THREE from 'three';
import { Html } from '@react-three/drei';
import { useFrame } from '@react-three/fiber';
import { useCollaborationStore } from './collaborationStore';

export default function RemoteCursors() {
  const remoteUsers = useCollaborationStore(s => s.remoteUsers);
  const users = Object.values(remoteUsers);

  const ringGeom = useMemo(() => new THREE.TorusGeometry(0.2, 0.04, 8, 16), []);

  return (
    <group>
      {users.map(user => (
        <RemoteCursorItem key={user.id} user={user} ringGeom={ringGeom} />
      ))}
    </group>
  );
}

function RemoteCursorItem({ user, ringGeom }: { user: { id: string; name: string; color: string; position: { x: number; y: number; z: number }; selectedId: string | null }; ringGeom: THREE.TorusGeometry }) {
  const meshRef = useRef<THREE.Mesh>(null!);
  const targetPos = useRef(new THREE.Vector3(user.position.x, user.position.y + 1.5, user.position.z));
  const currentPos = useRef(new THREE.Vector3(user.position.x, user.position.y + 1.5, user.position.z));

  // Update target when user position changes
  targetPos.current.set(user.position.x, user.position.y + 1.5, user.position.z);

  useFrame((_, delta) => {
    if (meshRef.current) {
      currentPos.current.lerp(targetPos.current, Math.min(5 * delta, 1));
      meshRef.current.position.copy(currentPos.current);
      meshRef.current.rotation.x += delta * 2;
      meshRef.current.rotation.y += delta * 1.5;
    }
  });

  return (
    <group>
      {/* Floating ring indicator */}
      <mesh ref={meshRef} geometry={ringGeom}>
        <meshStandardMaterial color={user.color} emissive={user.color} emissiveIntensity={0.6} />
      </mesh>
      {/* Username label */}
      <Html position={[0, 0.35, 0]} center distanceFactor={15} occlude={false}>
        <div className="text-[10px] whitespace-nowrap pointer-events-none px-1 py-0.5 rounded bg-slate-900/80 border" style={{ borderColor: user.color }}>
          <span style={{ color: user.color }}>{user.name}</span>
        </div>
      </Html>
    </group>
  );
}
