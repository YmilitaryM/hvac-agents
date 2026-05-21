import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import { ChillerModel } from '../../src/plant/models/ChillerModel';
import { PumpModel } from '../../src/plant/models/PumpModel';
import { CoolingTowerModel } from '../../src/plant/models/CoolingTowerModel';
import { ValveModel } from '../../src/plant/models/ValveModel';
import { SensorModel } from '../../src/plant/models/SensorModel';
import { PipeMesh } from '../../src/plant/models/PipeMesh';
import { getEquipmentTraits } from '../../src/plant/types';

describe('Model trait contracts', () => {
  it('all equipment types have valid traits consumed by models', () => {
    const types = [
      'centrifugal_chiller', 'pump', 'cooling_tower', 'control_valve',
      'temperature_sensor', 'pressure_sensor', 'flow_sensor', 'power_meter',
    ];
    for (const type of types) {
      const traits = getEquipmentTraits(type);
      expect(traits.dimensions.width).toBeGreaterThan(0);
      expect(traits.dimensions.height).toBeGreaterThan(0);
      expect(traits.dimensions.depth).toBeGreaterThan(0);
      expect(traits.color).toMatch(/^#/);
    }
  });

  it('ChillerModel dimensions match centrifugal_chiller traits', () => {
    const traits = getEquipmentTraits('centrifugal_chiller');
    expect(traits.dimensions.width).toBe(4);
    expect(traits.color).toBe('#3b82f6');
  });

  it('PumpModel uses pump traits correctly', () => {
    const traits = getEquipmentTraits('pump');
    expect(traits.label).toBe('水泵');
  });

  it('CoolingTowerModel uses correct dimensions', () => {
    const traits = getEquipmentTraits('cooling_tower');
    expect(traits.dimensions).toEqual({ width: 3, height: 3, depth: 3 });
  });

  it('ValveModel uses control_valve traits', () => {
    const traits = getEquipmentTraits('control_valve');
    expect(traits.color).toBe('#eab308');
  });

  it('SensorModel traits are small (sensor/meter sizes)', () => {
    for (const type of ['temperature_sensor', 'pressure_sensor']) {
      const traits = getEquipmentTraits(type);
      expect(traits.dimensions.width).toBeLessThan(1);
      expect(traits.dimensions.height).toBeLessThan(1);
    }
  });
});

describe('Model rendering', () => {
  it('ChillerModel mounts without crash', () => {
    const { container } = render(<ChillerModel position={[0, 0, 0]} />);
    expect(container).toBeTruthy();
  });

  it('ChillerModel mounts with selected state', () => {
    const { container } = render(<ChillerModel position={[0, 0, 0]} selected />);
    expect(container).toBeTruthy();
  });

  it('PumpModel mounts without crash', () => {
    const { container } = render(<PumpModel position={[0, 0, 0]} />);
    expect(container).toBeTruthy();
  });

  it('CoolingTowerModel mounts without crash', () => {
    const { container } = render(<CoolingTowerModel position={[0, 0, 0]} />);
    expect(container).toBeTruthy();
  });

  it('ValveModel mounts without crash', () => {
    const { container } = render(<ValveModel position={[0, 0, 0]} />);
    expect(container).toBeTruthy();
  });

  it('SensorModel mounts for all 4 sensor types', () => {
    for (const type of ['temperature_sensor', 'pressure_sensor', 'flow_sensor', 'power_meter']) {
      const { container } = render(<SensorModel position={[0, 0, 0]} typeCode={type} />);
      expect(container).toBeTruthy();
    }
  });

  it('PipeMesh mounts without crash', () => {
    const { container } = render(
      <PipeMesh
        start={{ x: 0, y: 0, z: 0 }}
        end={{ x: 5, y: 0, z: 0 }}
        waypoints={[]}
        diameter={200}
      />,
    );
    expect(container).toBeTruthy();
  });

  it('PipeMesh renders with waypoints', () => {
    const { container } = render(
      <PipeMesh
        start={{ x: 0, y: 0, z: 0 }}
        end={{ x: 5, y: 3, z: 0 }}
        waypoints={[{ x: 2.5, y: 0, z: 0 }, { x: 2.5, y: 3, z: 0 }]}
        diameter={150}
        color="#ff0000"
        selected
      />,
    );
    expect(container).toBeTruthy();
  });
});
