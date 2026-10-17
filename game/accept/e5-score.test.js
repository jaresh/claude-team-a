// Acceptance test for run e5 (lead-owned; teammates do not edit it).
import test from 'node:test';
import assert from 'node:assert/strict';
import { score } from '../src/core/score.js';
import { newGame, act, getView } from '../src/core/game.js';
import { FLOOR } from '../src/core/map.js';
import { MONSTERS } from '../src/data/monsters.js';
import { ITEMS } from '../src/data/items.js';
import { TRAPS } from '../src/data/traps.js';

const DIRS = [[1, 0], [-1, 0], [0, 1], [0, -1], [1, 1], [-1, -1], [1, -1], [-1, 1]];

// A new game with nothing on the level, and a floor tile next to the player.
function bare(seed = 11) {
  const state = newGame(seed);
  state.monsters = [];
  state.items = [];
  state.traps = [];
  const { x, y } = state.player;
  const [dx, dy] = DIRS.find(([dx, dy]) => state.map.tiles[(y + dy) * state.map.w + x + dx] === FLOOR);
  return { state, dx, dy, spot: { x: x + dx, y: y + dy } };
}

test('score formula', () => {
  const stats = { kills: { rat: 2, goblin: 1 }, itemsUsed: 2, trapsTriggered: 3, deepest: 4, damageTaken: 30 };
  assert.equal(score(stats, 'playing'), 400 + 30 + 10 - 6);
  assert.equal(score(stats, 'dead'), 400 + 30 + 10 - 6);
  assert.equal(score(stats, 'won'), 400 + 30 + 10 - 6 + 500);
  assert.equal(score({ kills: {}, itemsUsed: 0, trapsTriggered: 100, deepest: 1, damageTaken: 0 }, 'dead'), 0);
});

test('a new game starts with empty stats', () => {
  assert.deepEqual(newGame(5).stats, { kills: {}, itemsUsed: 0, trapsTriggered: 0, deepest: 1, damageTaken: 0 });
});

test('kills are counted by kind', () => {
  const { state, dx, dy, spot } = bare();
  const row = MONSTERS[0];
  state.monsters = [{ ...row, id: 9001, x: spot.x, y: spot.y, hp: 1, maxHp: 1, def: 0, ability: null }];
  act(state, { type: 'move', dx, dy });
  assert.equal(state.monsters.length, 0);
  assert.deepEqual(state.stats.kills, { [row.kind]: 1 });
});

test('used items, fired traps and the deepest depth are counted, across levels', () => {
  const { state, dx, dy, spot } = bare();
  const potion = ITEMS.find((it) => it.effect === 'heal');
  state.player.inventory = [{ ...potion, id: 9002, x: 0, y: 0 }];
  act(state, { type: 'use', index: 0 });
  assert.equal(state.stats.itemsUsed, 1);
  const spike = TRAPS.find((t) => t.effect === 'damage');
  state.traps = [{ ...spike, id: 9003, x: spot.x, y: spot.y, hidden: true }];
  const hp = state.player.hp;
  act(state, { type: 'move', dx, dy });
  assert.equal(state.stats.trapsTriggered, 1);
  assert.ok(state.stats.damageTaken > 0);
  assert.equal(state.stats.damageTaken, hp - state.player.hp);
  state.player.x = state.map.stairs.x;
  state.player.y = state.map.stairs.y;
  act(state, { type: 'descend' });
  assert.equal(state.depth, 2);
  assert.equal(state.stats.deepest, 2);
  assert.equal(state.stats.itemsUsed, 1);
  assert.equal(state.stats.trapsTriggered, 1);
});

test('damage taken counts monster hits and poison', () => {
  const { state, spot } = bare();
  const row = MONSTERS.find((m) => m.ability === 'poison');
  state.monsters = [{ ...row, id: 9004, x: spot.x, y: spot.y, hp: 50, maxHp: 50 }];
  const hp = state.player.hp;
  for (let i = 0; i < 3; i++) act(state, { type: 'wait' });
  assert.ok(state.player.hp < hp);
  assert.equal(state.stats.damageTaken, hp - state.player.hp);
});

test('the view has a deep copy of the stats, and the score', () => {
  const { state } = bare();
  const view = getView(state);
  assert.deepEqual(view.stats, state.stats);
  assert.equal(view.score, score(state.stats, state.status));
  view.stats.itemsUsed = 99;
  view.stats.kills.rat = 5;
  assert.equal(state.stats.itemsUsed, 0);
  assert.deepEqual(state.stats.kills, {});
});
