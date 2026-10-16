import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createRng } from '../src/core/rng.js';
import { generateMap, WALL, FLOOR, STAIRS, isWalkable, inBounds, isOpaque } from '../src/core/map.js';

const SEEDS = Array.from({ length: 20 }, (_, i) => i + 1);

function bfs(map, start) {
  const seen = new Set([start.y * map.w + start.x]);
  const queue = [start];
  while (queue.length) {
    const { x, y } = queue.shift();
    for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
      const nx = x + dx, ny = y + dy;
      const i = ny * map.w + nx;
      if (!isWalkable(map, nx, ny) || seen.has(i)) continue;
      seen.add(i);
      queue.push({ x: nx, y: ny });
    }
  }
  return seen;
}

test('map has the requested size and a wall border', () => {
  const map = generateMap(createRng(3));
  assert.equal(map.w, 60);
  assert.equal(map.h, 30);
  assert.equal(map.tiles.length, map.w * map.h);
  for (let x = 0; x < map.w; x++) {
    assert.equal(map.tiles[x], WALL);
    assert.equal(map.tiles[(map.h - 1) * map.w + x], WALL);
  }
  for (let y = 0; y < map.h; y++) {
    assert.equal(map.tiles[y * map.w], WALL);
    assert.equal(map.tiles[y * map.w + map.w - 1], WALL);
  }
});

test('same seed gives the same map', () => {
  const a = generateMap(createRng(11));
  const b = generateMap(createRng(11));
  assert.deepEqual(a.tiles, b.tiles);
  assert.deepEqual(a.start, b.start);
  assert.deepEqual(a.stairs, b.stairs);
});

for (const seed of SEEDS) {
  test(`seed ${seed}: start and stairs are in different rooms, all tiles reachable`, () => {
    const map = generateMap(createRng(seed));

    assert.ok(map.rooms.length >= 2, 'at least two rooms');
    const inRoom = (r, p) => p.x >= r.x && p.x < r.x + r.w && p.y >= r.y && p.y < r.y + r.h;
    const first = map.rooms[0], last = map.rooms[map.rooms.length - 1];
    assert.ok(inRoom(first, map.start), 'start is in the first room');
    assert.ok(inRoom(last, map.stairs), 'stairs are in the last room');
    assert.ok(!inRoom(last, map.start), 'start is not in the stairs room');

    assert.ok(isWalkable(map, map.start.x, map.start.y), 'start is walkable');
    assert.equal(map.tiles[map.stairs.y * map.w + map.stairs.x], STAIRS);

    const reached = bfs(map, map.start);
    for (let i = 0; i < map.tiles.length; i++) {
      if (map.tiles[i] === FLOOR || map.tiles[i] === STAIRS) {
        assert.ok(reached.has(i), `tile ${i} (${i % map.w},${Math.floor(i / map.w)}) unreachable`);
      }
    }
    assert.ok(reached.has(map.stairs.y * map.w + map.stairs.x), 'stairs reachable');
  });
}

test('helpers: inBounds, isWalkable, isOpaque', () => {
  const map = generateMap(createRng(2));
  assert.equal(inBounds(map, -1, 0), false);
  assert.equal(inBounds(map, map.w, 0), false);
  assert.equal(inBounds(map, 0, map.h - 1), true);
  assert.equal(isOpaque(map, -1, 0), true);
  assert.equal(isOpaque(map, 0, 0), true);
  assert.equal(isWalkable(map, 0, 0), false);
  assert.equal(isWalkable(map, map.start.x, map.start.y), true);
  assert.equal(isOpaque(map, map.start.x, map.start.y), false);
});
