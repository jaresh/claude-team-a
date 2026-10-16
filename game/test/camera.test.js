import { test } from 'node:test';
import assert from 'node:assert/strict';
import { cameraWindow, MIN_CELL } from '../src/ui/camera.js';
import { newGame, getView } from '../src/ui/mock-game.js';

const view = (w, h, x, y) => ({ w, h, player: { x, y } });

test('MIN_CELL is 16 css px', () => {
  assert.equal(MIN_CELL, 16);
});

test('camera centres on the player when there is room', () => {
  assert.deepEqual(cameraWindow(view(60, 30, 30, 15), 20, 15), { x0: 20, y0: 8, cols: 20, rows: 15 });
});

test('camera clamps at each edge of the map', () => {
  assert.deepEqual(cameraWindow(view(60, 30, 1, 1), 20, 15), { x0: 0, y0: 0, cols: 20, rows: 15 });
  assert.deepEqual(cameraWindow(view(60, 30, 59, 29), 20, 15), { x0: 40, y0: 15, cols: 20, rows: 15 });
  assert.deepEqual(cameraWindow(view(60, 30, 1, 29), 20, 15), { x0: 0, y0: 15, cols: 20, rows: 15 });
});

test('camera window never exceeds a small map', () => {
  assert.deepEqual(cameraWindow(view(10, 8, 5, 4), 20, 15), { x0: 0, y0: 0, cols: 10, rows: 8 });
});

test('camera window is never larger than the requested size', () => {
  const win = cameraWindow(view(60, 30, 30, 15), 12, 9);
  assert.deepEqual(win, { x0: 24, y0: 11, cols: 12, rows: 9 });
});

test('camera window stays inside the map for every player tile', () => {
  const v = { w: 24, h: 14 };
  for (let y = 0; y < v.h; y++) {
    for (let x = 0; x < v.w; x++) {
      const win = cameraWindow({ ...v, player: { x, y } }, 10, 7);
      assert.ok(win.x0 >= 0 && win.x0 + win.cols <= v.w, `x window at ${x},${y}`);
      assert.ok(win.y0 >= 0 && win.y0 + win.rows <= v.h, `y window at ${x},${y}`);
      assert.ok(x >= win.x0 && x < win.x0 + win.cols, `player x in window at ${x},${y}`);
      assert.ok(y >= win.y0 && y < win.y0 + win.rows, `player y in window at ${x},${y}`);
    }
  }
});

test('mock view carries the player tile and the inventory', () => {
  const v = getView(newGame(11));
  assert.equal(typeof v.player.x, 'number');
  assert.equal(typeof v.player.y, 'number');
  assert.ok(Array.isArray(v.inventory));
});
