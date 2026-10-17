import test from 'node:test';
import assert from 'node:assert/strict';
import { TRAPS } from '../src/data/traps.js';
import { spawnMonsters, spawnItems, spawnTraps } from '../src/core/rules.js';
import { createRng } from '../src/core/rng.js';
import { generateMap, FLOOR } from '../src/core/map.js';
import { newGame, act, getView } from '../src/core/game.js';

const DIRS = [[1, 0], [-1, 0], [0, 1], [0, -1], [1, 1], [-1, -1], [1, -1], [-1, 1]];

// Puts a hidden trap of the given effect on a floor tile next to the player and clears monsters.
function onePlayerStep(effect, seed = 7) {
  const state = newGame(seed);
  state.monsters = [];
  const { map, player: p } = state;
  const [dx, dy] = DIRS.find(([dx, dy]) => map.tiles[(p.y + dy) * map.w + p.x + dx] === FLOOR);
  const spot = { x: p.x + dx, y: p.y + dy };
  const row = TRAPS.find((t) => t.effect === effect);
  state.traps = [{ ...row, id: 9999, x: spot.x, y: spot.y, hidden: true }];
  return { state, spot, row, step: { type: 'move', dx, dy }, back: { type: 'move', dx: -dx, dy: -dy } };
}

test('spawnTraps: 1 + depth traps, each on its own free tile, ids do not collide', () => {
  for (const depth of [1, 2, 4]) {
    const rng = createRng(100 + depth);
    const map = generateMap(rng);
    const occupied = new Set();
    const monsters = spawnMonsters(rng, map, depth, occupied);
    const items = spawnItems(rng, map, depth, occupied);
    const traps = spawnTraps(rng, map, depth, occupied);
    assert.equal(traps.length, 1 + depth);
    const ids = new Set([...monsters, ...items, ...traps].map((e) => e.id));
    assert.equal(ids.size, monsters.length + items.length + traps.length);
    for (const t of traps) {
      assert.equal(map.tiles[t.y * map.w + t.x], FLOOR);
      assert.equal(t.hidden, true);
      assert.ok(TRAPS.some((r) => r.kind === t.kind && r.minDepth <= depth));
    }
  }
});

test('spawnTraps: no free floor left gives no traps', () => {
  const rng = createRng(5);
  const map = generateMap(rng);
  const occupied = new Set(map.tiles.map((_, i) => i));
  assert.deepEqual(spawnTraps(rng, map, 3, occupied), []);
});

test('TRAPS: every row has the fields and effects are the three kinds', () => {
  for (const t of TRAPS) {
    for (const k of ['kind', 'glyph', 'color', 'effect', 'amount', 'minDepth']) assert.ok(k in t, `${t.kind}.${k}`);
  }
  assert.deepEqual(new Set(TRAPS.map((t) => t.effect)), new Set(['damage', 'poison', 'teleport']));
});

test('damage trap: loses amount hp, never below 1, logs the loss', () => {
  const { state, row, step, back } = onePlayerStep('damage');
  state.player.hp = 10;
  act(state, step);
  assert.equal(state.player.hp, 10 - row.amount);
  assert.ok(state.log.includes(`A ${row.kind} trap wounds you for ${row.amount}.`));
  act(state, back);
  state.player.hp = 2;
  act(state, step);
  assert.equal(state.player.hp, 1);
  assert.ok(state.log.includes(`A ${row.kind} trap wounds you for 1.`));
});

test('poison trap: poisons the player, then one tick is taken this turn', () => {
  const { state, step } = onePlayerStep('poison');
  const hp = state.player.hp;
  act(state, step);
  assert.equal(state.player.poison, 2);
  assert.equal(state.player.hp, hp - 1);
  assert.equal(state.traps[0].hidden, false);
});

test('teleport trap: moves the player to a free floor tile away from monsters and traps', () => {
  const { state, spot, step } = onePlayerStep('teleport');
  act(state, step);
  const p = state.player;
  assert.ok(!(p.x === spot.x && p.y === spot.y));
  assert.equal(state.map.tiles[p.y * state.map.w + p.x], FLOOR);
  assert.ok(!state.traps.some((t) => t.x === p.x && t.y === p.y));
  assert.ok(state.log.includes('A teleport trap moves you.'));
});

test('teleport trap: same seed gives the same landing tile', () => {
  const a = onePlayerStep('teleport');
  const b = onePlayerStep('teleport');
  act(a.state, a.step);
  act(b.state, b.step);
  assert.deepEqual([a.state.player.x, a.state.player.y], [b.state.player.x, b.state.player.y]);
});

test('monsters never trigger traps', () => {
  const { state, spot } = onePlayerStep('damage');
  state.player.x = 0;
  state.player.y = 0;
  state.monsters = [{ id: 1, kind: 'rat', glyph: 'r', color: '#fff', x: spot.x, y: spot.y, hp: 3, maxHp: 3, atk: 1, def: 0, xp: 1, ability: null }];
  const hp = state.player.hp;
  act(state, { type: 'wait' });
  assert.equal(state.traps[0].hidden, true);
  assert.equal(state.player.hp, hp);
});

test('a trap shows in the view only once revealed and on a visible tile', () => {
  const { state, spot, row, step, back } = onePlayerStep('damage');
  const i = spot.y * state.map.w + spot.x;
  let view = getView(state);
  assert.notEqual(view.cells[i].ch, row.glyph);
  assert.deepEqual(view.traps, []);
  act(state, step);
  act(state, back);
  view = getView(state);
  assert.equal(view.cells[i].ch, row.glyph);
  assert.deepEqual(view.traps, [{ kind: row.kind, glyph: row.glyph, color: row.color, x: spot.x, y: spot.y }]);
});

test('every new level gets traps, including after descend', () => {
  const state = newGame(11);
  assert.equal(state.traps.length, 2);
  state.player.x = state.map.stairs.x;
  state.player.y = state.map.stairs.y;
  act(state, { type: 'descend' });
  assert.equal(state.depth, 2);
  assert.equal(state.traps.length, 3);
  assert.ok(state.traps.every((t) => t.hidden));
});
