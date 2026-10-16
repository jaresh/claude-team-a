import { test } from 'node:test';
import assert from 'node:assert/strict';
import { cameraWindow, MIN_CELL } from '../src/ui/camera.js';

const view = (w, h, x, y) => ({ w, h, player: { x, y } });

test('camera window never runs past the map edge on any side', () => {
  for (let y = 0; y < 14; y++) {
    for (let x = 0; x < 24; x++) {
      const win = cameraWindow(view(24, 14, x, y), 10, 8);
      assert.ok(win.x0 >= 0 && win.x0 + win.cols <= 24, `x ${x} y ${y}`);
      assert.ok(win.y0 >= 0 && win.y0 + win.rows <= 14, `x ${x} y ${y}`);
    }
  }
});

test('camera window keeps the player inside the window', () => {
  for (let y = 0; y < 14; y++) {
    for (let x = 0; x < 24; x++) {
      const win = cameraWindow(view(24, 14, x, y), 10, 8);
      assert.ok(x >= win.x0 && x < win.x0 + win.cols, `x ${x}`);
      assert.ok(y >= win.y0 && y < win.y0 + win.rows, `y ${y}`);
    }
  }
});

test('camera on a map bigger than the screen uses the screen size', () => {
  assert.deepEqual(cameraWindow(view(60, 30, 30, 15), 20, 15), { x0: 20, y0: 8, cols: 20, rows: 15 });
});

test('camera on a small map covers the whole map', () => {
  assert.deepEqual(cameraWindow(view(10, 8, 0, 0), 20, 15), { x0: 0, y0: 0, cols: 10, rows: 8 });
  assert.deepEqual(cameraWindow(view(10, 8, 9, 7), 20, 15), { x0: 0, y0: 0, cols: 10, rows: 8 });
});

test('camera rounds the centre down for an odd window size', () => {
  // cols 5: the player is at offset 2 of 5 columns, so x0 is player.x - 2.
  assert.equal(cameraWindow(view(60, 30, 30, 15), 5, 5).x0, 28);
  assert.equal(cameraWindow(view(60, 30, 30, 15), 5, 5).y0, 13);
});

test('camera cells are at least 16 px', () => {
  assert.ok(MIN_CELL >= 16);
});
