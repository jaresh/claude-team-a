// Field of view by ray casting: a tile is visible when the line from the origin
// to it crosses no opaque tile in between. Opaque tiles at the end of a line
// (walls) are visible themselves.

import { inBounds, isOpaque } from './map.js';

function lineClear(map, x0, y0, x1, y1) {
  let x = x0, y = y0;
  const dx = Math.abs(x1 - x0), sx = x0 < x1 ? 1 : -1;
  const dy = -Math.abs(y1 - y0), sy = y0 < y1 ? 1 : -1;
  let err = dx + dy;
  for (;;) {
    if (x === x1 && y === y1) return true;
    if (!(x === x0 && y === y0) && isOpaque(map, x, y)) return false;
    const e2 = 2 * err;
    if (e2 >= dy) { err += dy; x += sx; }
    if (e2 <= dx) { err += dx; y += sy; }
  }
}

export function computeFov(map, x, y, radius) {
  const visible = new Set();
  visible.add(y * map.w + x);
  const r2 = radius * radius;
  for (let ty = y - radius; ty <= y + radius; ty++) {
    for (let tx = x - radius; tx <= x + radius; tx++) {
      if (!inBounds(map, tx, ty)) continue;
      const dx = tx - x, dy = ty - y;
      if (dx * dx + dy * dy > r2) continue;
      if (lineClear(map, x, y, tx, ty)) visible.add(ty * map.w + tx);
    }
  }
  return visible;
}
