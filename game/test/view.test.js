import test from 'node:test';
import assert from 'node:assert/strict';
import { newGame, getView } from '../src/core/game.js';

const item = (id, kind, glyph, effect) =>
  ({ id, kind, glyph, color: '#ffffff', effect, amount: 1, x: 0, y: 0 });

test('getView returns the player tile', () => {
  const s = newGame(7);
  assert.deepEqual(getView(s).player, { x: s.player.x, y: s.player.y });
});

test('getView returns inventory entries in inventory order with the view fields only', () => {
  const s = newGame(7);
  s.player.inventory.push(item(900, 'potion', '!', 'heal'), item(901, 'whetstone', '/', 'atk'));
  const { inventory } = getView(s);
  assert.deepEqual(inventory, [
    { kind: 'potion', glyph: '!', color: '#ffffff', effect: 'heal', amount: 1 },
    { kind: 'whetstone', glyph: '/', color: '#ffffff', effect: 'atk', amount: 1 },
  ]);
});

test('getView of an empty inventory is an empty list', () => {
  assert.deepEqual(getView(newGame(7)).inventory, []);
});

test('getView inventory is a copy, not the live inventory', () => {
  const s = newGame(7);
  s.player.inventory.push(item(900, 'potion', '!', 'heal'));
  getView(s).inventory.pop();
  assert.equal(s.player.inventory.length, 1);
});
