import { test } from 'node:test';
import assert from 'node:assert/strict';
import { newGame, act, getView } from '../src/core/game.js';

const item = (id, kind, glyph, effect, amount = 1) =>
  ({ id, kind, glyph, color: '#ffffff', effect, amount, x: 0, y: 0 });

test('view has the player position', () => {
  const s = newGame(7);
  assert.deepEqual(getView(s).player, { x: s.player.x, y: s.player.y });
  s.player.x += 1;
  assert.deepEqual(getView(s).player, { x: s.player.x, y: s.player.y });
});

test('view lists inventory entries in order, with only the view fields', () => {
  const s = newGame(7);
  s.player.inventory.push(item(900, 'potion', '!', 'heal', 8), item(901, 'whetstone', '/', 'atk', 1));
  const { inventory } = getView(s);
  assert.deepEqual(inventory, [
    { kind: 'potion', glyph: '!', color: '#ffffff', effect: 'heal', amount: 8 },
    { kind: 'whetstone', glyph: '/', color: '#ffffff', effect: 'atk', amount: 1 },
  ]);
});

test('view of an empty inventory is an empty list', () => {
  assert.deepEqual(getView(newGame(7)).inventory, []);
});

test('view inventory is a copy, not the player array', () => {
  const s = newGame(7);
  s.player.inventory.push(item(900, 'potion', '!', 'heal'));
  getView(s).inventory.pop();
  assert.equal(s.player.inventory.length, 1);
});

test('view inventory follows pickup and use', () => {
  const s = newGame(9);
  s.monsters = [];
  s.items = [item(77, 'potion', '!', 'heal', 8)];
  s.items[0].x = s.player.x;
  s.items[0].y = s.player.y;
  s.player.hp = 5;
  act(s, { type: 'pickup' });
  assert.equal(getView(s).inventory.length, 1);
  act(s, { type: 'use', index: 0 });
  assert.deepEqual(getView(s).inventory, []);
});
