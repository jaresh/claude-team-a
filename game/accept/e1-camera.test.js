// Acceptance test for run e1 (lead-owned; teammates do not edit it).
import test from 'node:test';
import assert from 'node:assert/strict';
import { cameraWindow, MIN_CELL } from '../src/ui/camera.js';

const view = (w, h, x, y) => ({ w, h, player: { x, y } });

test('camera centres on the player', () => {
  assert.deepEqual(cameraWindow(view(60, 30, 30, 15), 20, 15), { x0: 20, y0: 8, cols: 20, rows: 15 });
});

test('camera clamps at the top-left corner', () => {
  assert.deepEqual(cameraWindow(view(60, 30, 1, 1), 20, 15), { x0: 0, y0: 0, cols: 20, rows: 15 });
});

test('camera clamps at the bottom-right corner', () => {
  assert.deepEqual(cameraWindow(view(60, 30, 59, 29), 20, 15), { x0: 40, y0: 15, cols: 20, rows: 15 });
});

test('camera shrinks to a small map', () => {
  assert.deepEqual(cameraWindow(view(10, 8, 5, 4), 20, 15), { x0: 0, y0: 0, cols: 10, rows: 8 });
});

test('camera cells are at least 16 px', () => {
  assert.ok(MIN_CELL >= 16);
});
