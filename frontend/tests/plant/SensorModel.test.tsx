import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import { SensorModel } from '../../src/plant/models/SensorModel';

describe('SensorModel', () => {
  it('renders a temperature sensor without crashing', () => {
    const { container } = render(
      <SensorModel position={[0, 0, 0]} typeCode="temperature_sensor" />,
    );
    expect(container).toBeTruthy();
  });

  it('renders with selected wireframe', () => {
    const { container } = render(
      <SensorModel position={[1, 2, 3]} typeCode="flow_sensor" selected />,
    );
    expect(container).toBeTruthy();
  });

  it('renders all four sensor types without crashing', () => {
    const types = ['temperature_sensor', 'pressure_sensor', 'flow_sensor', 'power_meter'] as const;
    for (const type of types) {
      const { container } = render(
        <SensorModel position={[0, 0, 0]} typeCode={type} />,
      );
      expect(container).toBeTruthy();
    }
  });
});
