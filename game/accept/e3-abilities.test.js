// Acceptance test for run e3 (lead-owned; teammates do not edit it).
import test from 'node:test';
import assert from 'node:assert/strict';
import { MONSTERS } from '../src/data/monsters.js';
import { monsterStep } from '../src/core/rules.js';
import { newGame, act, getView } from '../src/core/game.js';

const ABILITIES = ['regen', 'poison', 'ranged'];

function room() {
  const w = 12, h = 5, tiles = [];
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) tiles.push(x === 0 || y === 0 || x === w - 1 || y === h - 1 ? '#' : '.');
  }
  return { w, h, tiles, rooms: [], start: { x: 1, y: 2 }, stairs: { x: 10, y: 2 } };
}
const fixedRng = { next: () => 0, int: (min) => min, pick: (arr) => arr[0] };
const monster = (fields) => ({ id: 900, kind: 'test', glyph: 't', color: '#ffffff', hp: 5, maxHp: 5,
  atk: 2, def: 0, xp: 0, ability: null, ...fields });

// A visible floor tile at Chebyshev distance `lo`..`hi` from the player.
function visibleFloor(state, lo, hi) {
  const { map, player } = state;
  for (const i of state.visible) {
    const x = i % map.w, y = Math.floor(i / map.w);
    const d = Math.max(Math.abs(x - player.x), Math.abs(y - player.y));
    if (map.tiles[i] === '.' && d >= lo && d <= hi) return { x, y };
  }
  return null;
}

test('every kind has an ability field and each ability is used', () => {
  for (const row of MONSTERS) assert.ok('ability' in row, row.kind);
  for (const a of ABILITIES) assert.ok(MONSTERS.some((row) => row.ability === a), a);
  assert.ok(MONSTERS.length >= 7, `${MONSTERS.length} kinds`);
});

test('spawned monsters carry their kind\'s ability', () => {
  for (const seed of [1, 2, 3]) {
    for (const m of newGame(seed).monsters) {
      assert.equal(m.ability, MONSTERS.find((row) => row.kind === m.kind).ability, m.kind);
    }
  }
});

test('a ranged monster shoots from 2 to 4 tiles, attacks when adjacent, moves when far', () => {
  const map = room(), player = { x: 2, y: 2 };
  const step = (x) => {
    const m = monster({ x, y: 2, ability: 'ranged' });
    return monsterStep(map, m, player, new Set([2 * map.w + x]), () => false, fixedRng);
  };
  for (const x of [4, 5, 6]) assert.deepEqual(step(x), { type: 'shoot' }, `distance ${x - 2}`);
  assert.deepEqual(step(3), { type: 'attack' });
  assert.equal(step(9).type, 'move');
});

test('shooting hurts the player and is logged', () => {
  const state = newGame(4);
  const spot = visibleFloor(state, 2, 4);
  assert.ok(spot, 'no visible floor tile 2-4 tiles away for seed 4');
  state.monsters = [monster({ ...spot, ability: 'ranged', atk: 3 })];
  const hp = state.player.hp;
  act(state, { type: 'wait' });
  assert.ok(state.player.hp < hp, 'player hp did not drop');
  assert.ok(state.log.some((line) => /shoots you/.test(line)), 'no "shoots you" log line');
});

test('regen monsters heal 1 hp per turn, up to maxHp', () => {
  const state = newGame(1);
  const { x, y } = state.map.stairs;
  state.monsters = [monster({ x, y, hp: 1, maxHp: 10, atk: 0, ability: 'regen' })];
  act(state, { type: 'wait' });
  assert.equal(state.monsters[0].hp, 2);
  state.monsters[0].hp = 10;
  act(state, { type: 'wait' });
  assert.equal(state.monsters[0].hp, 10);
});

test('poison costs 1 hp per turn while it lasts', () => {
  const state = newGame(1);
  state.monsters = [];
  state.player.poison = 2;
  const hp = state.player.hp;
  act(state, { type: 'wait' });
  assert.equal(state.player.hp, hp - 1);
  assert.equal(getView(state).hud.poison, 1);
  act(state, { type: 'wait' });
  act(state, { type: 'wait' });
  assert.equal(state.player.hp, hp - 2);
  assert.equal(getView(state).hud.poison, 0);
});

test('view lists the living monsters on visible tiles', () => {
  const state = newGame(1);
  const spot = visibleFloor(state, 1, 8);
  state.monsters = [monster({ ...spot, kind: 'seen', ability: 'regen' }),
    monster({ id: 901, ...state.map.stairs, kind: 'unseen' })];
  const visible = state.visible.has(state.map.stairs.y * state.map.w + state.map.stairs.x);
  const { visibleMonsters } = getView(state);
  assert.equal(visibleMonsters.length, visible ? 2 : 1);
  assert.equal(visibleMonsters[0].kind, 'seen');
  for (const key of ['kind', 'glyph', 'color', 'hp', 'maxHp', 'ability']) {
    assert.ok(key in visibleMonsters[0], key);
  }
});
