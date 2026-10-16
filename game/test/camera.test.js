import { test } from 'node:test';
import assert from 'node:assert/strict';
import { cameraWindow, MIN_CELL } from '../src/ui/camera.js';
import { layout } from '../src/ui/render.js';
import { buttonToAction } from '../src/ui/input.js';
import { newGame, getView } from '../src/ui/mock-game.js';

const view = (w, h, x, y) => ({ w, h, player: { x, y } });

test('window is centred on the player', () => {
  assert.deepEqual(cameraWindow(view(60, 30, 30, 15), 20, 15), { x0: 20, y0: 8, cols: 20, rows: 15 });
});

test('window clamps at each edge and corner', () => {
  assert.deepEqual(cameraWindow(view(60, 30, 0, 0), 20, 15), { x0: 0, y0: 0, cols: 20, rows: 15 });
  assert.deepEqual(cameraWindow(view(60, 30, 59, 29), 20, 15), { x0: 40, y0: 15, cols: 20, rows: 15 });
  assert.deepEqual(cameraWindow(view(60, 30, 2, 28), 20, 15), { x0: 0, y0: 15, cols: 20, rows: 15 });
});

test('window shrinks to a map smaller than the request', () => {
  assert.deepEqual(cameraWindow(view(10, 8, 5, 4), 20, 15), { x0: 0, y0: 0, cols: 10, rows: 8 });
  assert.deepEqual(cameraWindow(view(12, 40, 6, 20), 20, 15), { x0: 0, y0: 13, cols: 12, rows: 15 });
});

test('window with an odd size keeps the player inside it', () => {
  const win = cameraWindow(view(60, 30, 30, 15), 21, 15);
  assert.equal(win.cols, 21);
  assert.ok(win.x0 <= 30 && 30 < win.x0 + win.cols);
  assert.ok(win.y0 <= 15 && 15 < win.y0 + win.rows);
});

test('MIN_CELL is at least 16 css px', () => {
  assert.ok(MIN_CELL >= 16);
});

test('layout fits the map columns to a 360 px phone width', () => {
  const grid = layout(view(60, 30, 0, 0), 328);
  assert.equal(grid.cols, 20); // floor(328 / 16)
  assert.equal(grid.cell, 16); // floor(328 / 20)
  assert.equal(grid.rows, 15); // capped at 15 rows
  assert.equal(grid.cellH, 16 * 1.6);
});

test('layout uses the whole map when it fits and never returns zero', () => {
  const grid = layout(view(24, 14, 0, 0), 1000);
  assert.equal(grid.cols, 24);
  assert.equal(grid.rows, 14);
  assert.ok(layout(view(24, 14, 0, 0), 0).cols >= 1);
});

test('inventory use buttons map to use actions, bad indexes map to nothing', () => {
  assert.deepEqual(buttonToAction({ action: 'use', index: '2' }), { type: 'use', index: 2 });
  assert.equal(buttonToAction({ action: 'use' }), null);
  assert.equal(buttonToAction({ action: 'use', index: '-1' }), null);
  assert.equal(buttonToAction({ action: 'use', index: 'x' }), null);
});

test('mock view carries player and inventory', () => {
  const state = newGame(9);
  const v = getView(state);
  assert.deepEqual(v.player, { x: state.player.x, y: state.player.y });
  assert.deepEqual(v.inventory, []);
  state.player.inventory.push({ id: 5, kind: 'potion', glyph: '!', color: '#ff5fa2', effect: 'heal', amount: 8, x: 0, y: 0 });
  assert.equal(getView(state).inventory[0].kind, 'potion');
});
