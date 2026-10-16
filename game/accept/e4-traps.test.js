// Acceptance test for run e4 (lead-owned; teammates do not edit it).
import test from 'node:test';
import assert from 'node:assert/strict';
import { TRAPS } from '../src/data/traps.js';
import { spawnTraps } from '../src/core/rules.js';
import { createRng } from '../src/core/rng.js';
import { generateMap, isWalkable, FLOOR } from '../src/core/map.js';
import { newGame, act, getView } from '../src/core/game.js';

const DIRS = [[1, 0], [-1, 0], [0, 1], [0, -1], [1, 1], [-1, -1], [1, -1], [-1, 1]];

// A new game with no monsters and one hidden trap of `effect` next to the player.
function setup(effect) {
  const state = newGame(7);
  state.monsters = [];
  const { x, y } = state.player;
  const [dx, dy] = DIRS.find(([dx, dy]) => isWalkable(state.map, x + dx, y + dy)
    && state.map.tiles[(y + dy) * state.map.w + x + dx] === FLOOR);
  const spot = { x: x + dx, y: y + dy };
  state.items = state.items.filter((it) => !(it.x === spot.x && it.y === spot.y));
  const row = TRAPS.find((t) => t.effect === effect);
  state.traps = [{ ...row, id: 9999, x: spot.x, y: spot.y, hidden: true }];
  return { state, spot, row, onto: { type: 'move', dx, dy }, back: { type: 'move', dx: -dx, dy: -dy } };
}

test('trap table has the three effects', () => {
  assert.ok(TRAPS.length >= 3);
  for (const t of TRAPS) {
    for (const k of ['kind', 'glyph', 'color', 'effect', 'minDepth']) assert.ok(k in t, `${t.kind}.${k}`);
  }
  const effects = new Set(TRAPS.map((t) => t.effect));
  for (const e of ['damage', 'poison', 'teleport']) assert.ok(effects.has(e), e);
});

test('spawnTraps places 1 + depth hidden traps on free floor', () => {
  for (const depth of [1, 3, 5]) {
    const rng = createRng(40 + depth);
    const map = generateMap(rng);
    const blocked = map.rooms[0].y * map.w + map.rooms[0].x + 1;
    const occupied = new Set([blocked]);
    const traps = spawnTraps(rng, map, depth, occupied);
    assert.equal(traps.length, 1 + depth);
    const seen = new Set();
    for (const t of traps) {
      const i = t.y * map.w + t.x;
      assert.equal(map.tiles[i], FLOOR);
      assert.notEqual(i, blocked);
      assert.ok(!(t.x === map.start.x && t.y === map.start.y));
      assert.ok(occupied.has(i));
      assert.ok(!seen.has(i));
      seen.add(i);
      assert.equal(t.hidden, true);
      assert.ok(TRAPS.find((r) => r.kind === t.kind).minDepth <= depth);
    }
  }
});

test('every level has hidden traps', () => {
  const state = newGame(3);
  assert.equal(state.traps.length, 2);
  assert.ok(state.traps.every((t) => t.hidden));
  state.player.x = state.map.stairs.x;
  state.player.y = state.map.stairs.y;
  act(state, { type: 'descend' });
  assert.equal(state.depth, 2);
  assert.equal(state.traps.length, 3);
});

test('a damage trap fires every time, reveals itself, and leaves at least 1 hp', () => {
  const { state, spot, row, onto, back } = setup('damage');
  const hp = state.player.hp;
  act(state, onto);
  assert.deepEqual([state.player.x, state.player.y], [spot.x, spot.y]);
  assert.equal(state.player.hp, Math.max(1, hp - row.amount));
  assert.equal(state.traps[0].hidden, false);
  act(state, back);
  state.player.hp = 1;
  act(state, onto);
  assert.equal(state.player.hp, 1);
  const wounds = state.log.filter((l) => l.includes(`A ${row.kind} trap wounds you for`));
  assert.ok(wounds.length >= 2);
  assert.ok(!state.log.some((l) => l.includes('hits you')));
});

test('a poison trap poisons the player', () => {
  const { state, onto } = setup('poison');
  act(state, onto);
  assert.ok(state.player.poison >= 2 && state.player.poison <= 3, String(state.player.poison));
  assert.ok(state.log.some((l) => l.includes('A poison needle pricks you.')));
});

test('a teleport trap moves the player to another floor tile', () => {
  const { state, spot, onto } = setup('teleport');
  act(state, onto);
  const p = state.player;
  assert.ok(!(p.x === spot.x && p.y === spot.y));
  assert.equal(state.map.tiles[p.y * state.map.w + p.x], FLOOR);
  assert.equal(state.traps[0].hidden, false);
  assert.ok(state.log.some((l) => l.includes('A teleport trap moves you.')));
});

test('only revealed traps show in the view', () => {
  const { state, spot, row, onto, back } = setup('damage');
  const i = spot.y * state.map.w + spot.x;
  let view = getView(state);
  assert.notEqual(view.cells[i].ch, row.glyph);
  assert.deepEqual(view.traps, []);
  act(state, onto);
  act(state, back);
  view = getView(state);
  assert.equal(view.cells[i].ch, row.glyph);
  assert.deepEqual(view.traps, [{ kind: row.kind, glyph: row.glyph, color: row.color, x: spot.x, y: spot.y }]);
});
