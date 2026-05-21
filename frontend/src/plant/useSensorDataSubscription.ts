import { useEffect, useRef } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';
import { useSensorDataStore } from './sensorDataStore';
import { usePlantStore } from './store';
import { getPointDefs } from './types';

const SIMULATED_POINTS: Record<string, () => number> = {
  power_kw: () => +(50 + Math.random() * 200).toFixed(1),
  current_load_rt: () => +(100 + Math.random() * 400).toFixed(0),
  speed_hz: () => +(20 + Math.random() * 30).toFixed(1),
  flow_lps: () => +(5 + Math.random() * 20).toFixed(1),
  water_out_temp: () => +(25 + Math.random() * 10).toFixed(1),
  fan_power_kw: () => +(3 + Math.random() * 12).toFixed(1),
  measured_temp: () => +(18 + Math.random() * 15).toFixed(1),
  measured_pressure: () => +(100 + Math.random() * 300).toFixed(1),
  measured_flow: () => +(5 + Math.random() * 20).toFixed(1),
  measured_power: () => +(10 + Math.random() * 100).toFixed(1),
  valve_position: () => +(Math.random() * 100).toFixed(0),
  run_status: () => (Math.random() > 0.1 ? '运行' : '停止'),
};

export function useSensorDataSubscription() {
  const updateReading = useSensorDataStore(s => s.updateReading);
  const equipment = usePlantStore(s => s.equipment);
  const eqRef = useRef(equipment);
  eqRef.current = equipment;

  const { status } = useWebSocket({
    onMessage: (data) => {
      if (data.type === 'sensor_reading' && typeof data.equipment_id === 'string' && typeof data.point_code === 'string') {
        updateReading(data.equipment_id, data.point_code, data.value as number | string);
      }
    },
  });

  // Dev-mode simulation: generate fake sensor data every 3s when WebSocket is not connected
  useEffect(() => {
    if (status === 'connected') return;

    const interval = setInterval(() => {
      const eqs = eqRef.current;
      for (const eq of eqs) {
        const points = getPointDefs(eq.type_code).filter(p => p.io_direction === 'output' || p.io_direction === 'calc');
        for (const p of points.slice(0, 3)) {
          const gen = SIMULATED_POINTS[p.code];
          if (gen) {
            updateReading(eq.id, p.code, gen());
          }
        }
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [status, updateReading]);
}
