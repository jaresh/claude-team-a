// Acceptance test for run e1 (lead-owned; teammates do not edit it).
import test from 'node:test';
import assert from 'node:assert/strict';
import { newGame, getView } from '../src/core/game.js';

const item = (id, kind, glyph, effect) =>
  ({ id, kind, glyph, color: '#ffffff', effect, amount: 1, x: 0, y: 0 });

test('view has the player position', () => {
  const state = newGame(7);
  assert.deepEqual(getView(state).player, { x: state.player.x, y: state.player.y });
});

test('view lists the inventory in order', () => {
  const state = newGame(7);
  state.player.inventory.push(item(900, 'potion', '!', 'heal'), item(901, 'whetstone', '/', 'atk'));
  const { inventory } = getView(state);
  assert.equal(inventory.length, 2);
  assert.equal(inventory[0].kind, 'potion');
  assert.equal(inventory[1].glyph, '/');
  for (const entry of inventory) {
    for (const key of ['kind', 'glyph', 'color', 'effect', 'amount']) assert.ok(key in entry, key);
  }
});

test('view of an empty inventory is an empty list', () => {
  assert.deepEqual(getView(newGame(7)).inventory, []);
});
