export interface Point3D {
  x: number;
  y: number;
  z: number;
}

function dist(a: Point3D, b: Point3D): number {
  return Math.sqrt((b.x - a.x) ** 2 + (b.y - a.y) ** 2 + (b.z - a.z) ** 2);
}

/**
 * Compute pipe routing waypoints between two 3D points.
 *
 * - If start and end are (near) the same point, returns [] (straight pipe).
 * - If there is a vertical offset (dy), produces a Z-path: two waypoints
 *   (horizontal halfway, then vertical, then horizontal to end).
 * - If only horizontal offset, produces an L-path: one turn point on the
 *   dominant horizontal axis.
 */
export function computePipePath(start: Point3D, end: Point3D): Point3D[] {
  const dx = end.x - start.x;
  const dy = end.y - start.y;
  const dz = end.z - start.z;

  if (Math.abs(dx) < 0.01 && Math.abs(dy) < 0.01 && Math.abs(dz) < 0.01) {
    return [];
  }

  if (Math.abs(dy) > 0.01 && (Math.abs(dx) > 0.01 || Math.abs(dz) > 0.01)) {
    // Z-path: horizontal midpoint -> vertical -> horizontal finish
    if (Math.abs(dx) >= Math.abs(dz)) {
      return [
        { x: start.x + dx * 0.5, y: start.y, z: start.z },
        { x: start.x + dx * 0.5, y: end.y, z: end.z },
      ];
    } else {
      return [
        { x: start.x, y: start.y, z: start.z + dz * 0.5 },
        { x: end.x, y: start.y, z: start.z + dz * 0.5 },
      ];
    }
  }

  // L-path: one turn point on the dominant horizontal axis
  if (Math.abs(dx) >= Math.abs(dz)) {
    return [{ x: end.x, y: start.y, z: start.z }];
  } else {
    return [{ x: start.x, y: start.y, z: end.z }];
  }
}

/**
 * Compute total pipe length from start to end, passing through waypoints.
 * Result is rounded to 2 decimal places.
 */
export function computePipeLength(
  start: Point3D,
  end: Point3D,
  waypoints: Point3D[],
): number {
  let total = 0;
  let prev = start;
  for (const wp of waypoints) {
    total += dist(prev, wp);
    prev = wp;
  }
  total += dist(prev, end);
  return Math.round(total * 100) / 100;
}
