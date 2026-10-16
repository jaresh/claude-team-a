import { test } from 'node:test';
import assert from 'node:assert/strict';
import { computeFov } from '../src/core/fov.js';

function makeMap(rows) {
  const h = rows.length, w = rows[0].length;
  return { w, h, tiles: rows.join('').split(''), rooms: [], start: null, stairs: null };
}

const ROWS = [
  '##########',
  '#........#',
  '#...#....#',
  '#........#',
  '##########',
];
const map = makeMap(ROWS);
const idx = (x, y) => y * map.w + x;

test('FOV includes the origin', () => {
  const vis = computeFov(map, 2, 2, 8);
  assert.ok(vis.has(idx(2, 2)));
});

test('FOV includes a seen wall', () => {
  const vis = computeFov(map, 2, 2, 8);
  assert.ok(vis.has(idx(0, 2)), 'border wall in view');
  assert.ok(vis.has(idx(4, 2)), 'pillar in view');
});

test('FOV excludes a tile behind a wall', () => {
  const vis = computeFov(map, 2, 2, 8);
  assert.equal(vis.has(idx(5, 2)), false);
  assert.equal(vis.has(idx(7, 2)), false);
});

test('FOV respects the radius', () => {
  const vis = computeFov(map, 1, 1, 2);
  assert.equal(vis.has(idx(8, 1)), false);
  assert.equal(vis.has(idx(3, 1)), true);
});

test('FOV only holds in-bounds indices', () => {
  const vis = computeFov(map, 1, 1, 20);
  for (const i of vis) {
    assert.ok(i >= 0 && i < map.w * map.h);
  }
});
