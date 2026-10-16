// Dungeon generation: non-overlapping rooms joined by L-shaped corridors.

export const WALL = '#', FLOOR = '.', STAIRS = '>';

function idx(map, x, y) {
  return y * map.w + x;
}

export function inBounds(map, x, y) {
  return Number.isInteger(x) && Number.isInteger(y) && x >= 0 && y >= 0 && x < map.w && y < map.h;
}

export function isWalkable(map, x, y) {
  if (!inBounds(map, x, y)) return false;
  const t = map.tiles[idx(map, x, y)];
  return t === FLOOR || t === STAIRS;
}

export function isOpaque(map, x, y) {
  if (!inBounds(map, x, y)) return true;
  return map.tiles[idx(map, x, y)] === WALL;
}

function overlaps(a, b) {
  // Rooms must keep a one-tile gap between them.
  return a.x < b.x + b.w + 1 && b.x < a.x + a.w + 1 && a.y < b.y + b.h + 1 && b.y < a.y + a.h + 1;
}

function center(room) {
  return { x: room.x + Math.floor(room.w / 2), y: room.y + Math.floor(room.h / 2) };
}

function attempt(rng, w, h, maxRooms, minRoom, maxRoom) {
  const tiles = new Array(w * h).fill(WALL);
  const map = { w, h, tiles, rooms: [], start: null, stairs: null };
  const rooms = map.rooms;
  const put = (x, y, t) => {
    tiles[y * w + x] = t;
  };

  let tries = maxRooms * 10;
  while (rooms.length < maxRooms && tries-- > 0) {
    const rw = rng.int(minRoom, maxRoom);
    const rh = rng.int(minRoom, maxRoom);
    if (rw > w - 2 || rh > h - 2) continue;
    const x = rng.int(1, w - 1 - rw);
    const y = rng.int(1, h - 1 - rh);
    const room = { x, y, w: rw, h: rh };
    if (rooms.some((r) => overlaps(r, room))) continue;
    rooms.push(room);
  }
  if (rooms.length < 2) return null;

  for (const r of rooms) {
    for (let yy = r.y; yy < r.y + r.h; yy++) {
      for (let xx = r.x; xx < r.x + r.w; xx++) put(xx, yy, FLOOR);
    }
  }

  // Join each room to the previous one. Centers are inside the interior, so
  // corridors never touch the border.
  for (let i = 1; i < rooms.length; i++) {
    const a = center(rooms[i - 1]);
    const b = center(rooms[i]);
    const x0 = Math.min(a.x, b.x), x1 = Math.max(a.x, b.x);
    for (let xx = x0; xx <= x1; xx++) put(xx, a.y, FLOOR);
    const y0 = Math.min(a.y, b.y), y1 = Math.max(a.y, b.y);
    for (let yy = y0; yy <= y1; yy++) put(b.x, yy, FLOOR);
  }

  map.start = center(rooms[0]);
  map.stairs = center(rooms[rooms.length - 1]);
  put(map.stairs.x, map.stairs.y, STAIRS);
  return map;
}

export function generateMap(rng, opts = {}) {
  const w = opts.w ?? 60;
  const h = opts.h ?? 30;
  const maxRooms = opts.maxRooms ?? 12;
  const minRoom = opts.minRoom ?? 4;
  const maxRoom = opts.maxRoom ?? 10;
  for (let i = 0; i < 100; i++) {
    const map = attempt(rng, w, h, maxRooms, minRoom, maxRoom);
    if (map) return map;
  }
  throw new Error('generateMap: could not place two rooms');
}
