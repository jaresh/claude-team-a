import test from 'node:test';
import assert from 'node:assert/strict';
import { TRAPS } from '../src/data/traps.js';
import { spawnTraps } from '../src/core/rules.js';
import { createRng } from '../src/core/rng.js';
import { generateMap, FLOOR } from '../src/core/map.js';
import { newGame, act } from '../src/core/game.js';

// A direction whose tile from the player is floor. The player never stands on the map edge.
function floorStep(state) {
  const { map, player: p } = state;
  const dirs = [[1, 0], [-1, 0], [0, 1], [0, -1]];
  const [dx, dy] = dirs.find(([dx, dy]) => map.tiles[(p.y + dy) * map.w + p.x + dx] === FLOOR);
  return { dx, dy };
}

test('depth 1 traps are all spikes, since only spikes start at depth 1', () => {
  const rng = createRng(5);
  const map = generateMap(rng);
  const traps = spawnTraps(rng, map, 1, new Set());
  assert.equal(traps.length, 2);
  for (const t of traps) assert.equal(t.kind, 'spike');
});

test('trap ids do not collide with monster or item ids on a level', () => {
  for (const seed of [1, 2, 3]) {
    const state = newGame(seed);
    const ids = [...state.monsters, ...state.items, ...state.traps].map((e) => e.id);
    assert.equal(new Set(ids).size, ids.length, `seed ${seed}`);
  }
});

test('every trap kind has a distinct colour', () => {
  const colours = new Set(TRAPS.map((t) => t.color));
  assert.equal(colours.size, TRAPS.length);
});

test('a damage trap logs the real loss and never leaves the player below 1 hp', () => {
  const state = newGame(4);
  state.monsters = [];
  const { dx, dy } = floorStep(state);
  const { x, y } = state.player;
  state.traps = [{ id: 9999, kind: 'spike', glyph: '^', color: '#c9d1d9', effect: 'damage', amount: 5,
    x: x + dx, y: y + dy, hidden: true }];
  state.player.hp = 3;
  act(state, { type: 'move', dx, dy });
  assert.equal(state.player.hp, 1);
  assert.ok(state.log.includes('A spike trap wounds you for 2.'), state.log.join(' | '));
});

test('stepping next to a trap without entering its tile does not fire it', () => {
  const state = newGame(4);
  state.monsters = [];
  const { dx, dy } = floorStep(state);
  const { x, y } = state.player;
  state.traps = [{ id: 9999, kind: 'spike', glyph: '^', color: '#c9d1d9', effect: 'damage', amount: 5,
    x: x + 2 * dx, y: y + 2 * dy, hidden: true }];
  const hp = state.player.hp;
  act(state, { type: 'move', dx, dy });
  assert.equal(state.player.hp, hp);
  assert.equal(state.traps[0].hidden, true);
});
