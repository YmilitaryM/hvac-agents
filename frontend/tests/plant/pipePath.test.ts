import { describe, it, expect } from 'vitest';
import { computePipePath, computePipeLength, type Point3D } from '../../src/plant/pipePath';

describe('computePipePath', () => {
  it('returns empty waypoints for same position (no offset)', () => {
    const start: Point3D = { x: 1, y: 1, z: 1 };
    const end: Point3D = { x: 1, y: 1, z: 1 };
    const waypoints = computePipePath(start, end);
    expect(waypoints).toHaveLength(0);
  });

  it('returns empty waypoints for zero-length straight pipe', () => {
    const start: Point3D = { x: 0, y: 0, z: 0 };
    const end: Point3D = { x: 0, y: 0, z: 0 };
    const waypoints = computePipePath(start, end);
    expect(waypoints).toHaveLength(0);
  });

  it('generates L-path (one turn point) when X axis is dominant and no vertical offset', () => {
    const start: Point3D = { x: 0, y: 0, z: 0 };
    const end: Point3D = { x: 5, y: 0, z: 2 };
    const waypoints = computePipePath(start, end);
    expect(waypoints).toHaveLength(1);
    expect(waypoints[0].x).toBeCloseTo(5);
    expect(waypoints[0].y).toBe(0);
    expect(waypoints[0].z).toBe(0);
  });

  it('generates L-path (one turn point) when Z axis is dominant and no vertical offset', () => {
    const start: Point3D = { x: 0, y: 0, z: 0 };
    const end: Point3D = { x: 2, y: 0, z: 5 };
    const waypoints = computePipePath(start, end);
    expect(waypoints).toHaveLength(1);
    expect(waypoints[0].x).toBe(0);
    expect(waypoints[0].y).toBe(0);
    expect(waypoints[0].z).toBeCloseTo(5);
  });

  it('generates Z-path (two waypoints) when there is a vertical offset', () => {
    const start: Point3D = { x: 0, y: 0, z: 0 };
    const end: Point3D = { x: 3, y: 4, z: 0 };
    const waypoints = computePipePath(start, end);
    expect(waypoints).toHaveLength(2);
    // First waypoint: halfway on dominant horizontal (X), at start Y and start Z
    expect(waypoints[0].x).toBeCloseTo(1.5);
    expect(waypoints[0].y).toBe(0);
    expect(waypoints[0].z).toBe(0);
    // Second waypoint: same X, at end Y, at end Z
    expect(waypoints[1].x).toBeCloseTo(1.5);
    expect(waypoints[1].y).toBe(4);
    expect(waypoints[1].z).toBe(0);
  });

  it('generates Z-path when Z is dominant with vertical offset', () => {
    const start: Point3D = { x: 0, y: 0, z: 0 };
    const end: Point3D = { x: 1, y: 4, z: 5 };
    const waypoints = computePipePath(start, end);
    expect(waypoints).toHaveLength(2);
    // First waypoint: halfway on dominant horizontal (Z), at start Y
    expect(waypoints[0].x).toBe(0);
    expect(waypoints[0].y).toBe(0);
    expect(waypoints[0].z).toBeCloseTo(2.5);
    // Second waypoint: at end X, start Y, same Z as first
    expect(waypoints[1].x).toBe(1);
    expect(waypoints[1].y).toBe(0);
    expect(waypoints[1].z).toBeCloseTo(2.5);
  });
});

describe('computePipeLength', () => {
  it('computes straight line length (no waypoints)', () => {
    const waypoints: Point3D[] = [];
    const length = computePipeLength({ x: 0, y: 0, z: 0 }, { x: 3, y: 4, z: 0 }, waypoints);
    expect(length).toBeCloseTo(5);
  });

  it('computes length through waypoints', () => {
    const waypoints: Point3D[] = [{ x: 3, y: 0, z: 0 }];
    const length = computePipeLength({ x: 0, y: 0, z: 0 }, { x: 3, y: 0, z: 4 }, waypoints);
    expect(length).toBeCloseTo(7);
  });

  it('computes Z-path total length', () => {
    const waypoints: Point3D[] = [
      { x: 1.5, y: 0, z: 0 },
      { x: 1.5, y: 4, z: 0 },
    ];
    // start->wp0: 1.5, wp0->wp1: 4, wp1->end: 1.5, total = 7
    const length = computePipeLength({ x: 0, y: 0, z: 0 }, { x: 3, y: 4, z: 0 }, waypoints);
    expect(length).toBeCloseTo(7);
  });

  it('rounds length to 2 decimal places', () => {
    const waypoints: Point3D[] = [];
    // sqrt(2) ≈ 1.4142..., rounded to 1.41
    const length = computePipeLength({ x: 0, y: 0, z: 0 }, { x: 1, y: 1, z: 0 }, waypoints);
    expect(length).toBeCloseTo(1.41);
  });
});
