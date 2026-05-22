import { Html } from '@react-three/drei';
import { usePlantStore } from './store';
import { useSensorDataStore } from './sensorDataStore';
import { getPointDefs } from './types';

function statusColor(code: string, value: number | string): string {
  if (typeof value === 'string') return '#22d3ee';
  const n = value as number;
  switch (code) {
    case 'power_kw':
    case 'fan_power_kw':
    case 'measured_power':
      return n > 200 ? '#ef4444' : n > 120 ? '#eab308' : '#22d3ee';
    case 'current_load_rt':
      return n > 350 ? '#ef4444' : n > 250 ? '#eab308' : '#22d3ee';
    case 'speed_hz':
      return n > 48 ? '#ef4444' : n > 42 ? '#eab308' : '#22d3ee';
    case 'water_out_temp':
    case 'measured_temp':
      return n > 32 ? '#ef4444' : n > 28 ? '#eab308' : '#22d3ee';
    default:
      return '#22d3ee';
  }
}

export default function SensorOverlay() {
  const equipment = usePlantStore(s => s.equipment);
  const readings = useSensorDataStore(s => s.readings);

  return (
    <group>
      {equipment.map(eq => {
        const points = getPointDefs(eq.type_code)
          .filter(p => p.io_direction === 'output' || p.io_direction === 'calc')
          .slice(0, 2);

        const displayPoints = points.filter(p => readings[`${eq.id}:${p.code}`]);

        if (displayPoints.length === 0) return null;

        return (
          <Html
            key={eq.id}
            position={[eq.position.x, eq.position.y + 2.2, eq.position.z]}
            center
            distanceFactor={15}
            occlude={false}
          >
            <div className="bg-slate-900/90 border border-slate-700 rounded px-1.5 py-0.5 text-[10px] leading-tight whitespace-nowrap pointer-events-none">
              {displayPoints.map(p => {
                const r = readings[`${eq.id}:${p.code}`];
                const color = statusColor(p.code, r.value);
                return (
                  <div key={p.code} className="flex gap-1.5 items-center">
                    <span className="text-slate-500">{p.name}</span>
                    <span style={{ color }}>
                      {typeof r.value === 'number' ? r.value.toFixed(1) : r.value}
                      <span className="text-slate-600 ml-0.5">{p.unit}</span>
                    </span>
                  </div>
                );
              })}
            </div>
          </Html>
        );
      })}
    </group>
  );
}
