import { test } from 'node:test';
import assert from 'node:assert/strict';
import { newGame, getView } from '../src/core/game.js';

const item = (id, kind, glyph, effect, amount = 1) =>
  ({ id, kind, glyph, color: '#ffffff', effect, amount, x: 0, y: 0 });

test('getView returns the player tile', () => {
  const s = newGame(7);
  assert.deepEqual(getView(s).player, { x: s.player.x, y: s.player.y });
});

test('getView player follows the player position', () => {
  const s = newGame(7);
  s.player.x = 3;
  s.player.y = 4;
  assert.deepEqual(getView(s).player, { x: 3, y: 4 });
});

test('getView inventory is empty for a new game', () => {
  assert.deepEqual(getView(newGame(7)).inventory, []);
});

test('getView inventory lists items in inventory order', () => {
  const s = newGame(7);
  s.player.inventory.push(item(900, 'potion', '!', 'heal', 4), item(901, 'whetstone', '/', 'atk', 2));
  assert.deepEqual(getView(s).inventory, [
    { kind: 'potion', glyph: '!', color: '#ffffff', effect: 'heal', amount: 4 },
    { kind: 'whetstone', glyph: '/', color: '#ffffff', effect: 'atk', amount: 2 },
  ]);
});

test('getView inventory entries carry only the view fields', () => {
  const s = newGame(7);
  s.player.inventory.push(item(900, 'potion', '!', 'heal'));
  const [entry] = getView(s).inventory;
  assert.deepEqual(Object.keys(entry).sort(), ['amount', 'color', 'effect', 'glyph', 'kind']);
});

test('getView inventory is a copy that does not alias player items', () => {
  const s = newGame(7);
  s.player.inventory.push(item(900, 'potion', '!', 'heal'));
  getView(s).inventory.pop();
  assert.equal(s.player.inventory.length, 1);
});
