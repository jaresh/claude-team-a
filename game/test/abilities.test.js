import { test } from 'node:test';
import assert from 'node:assert/strict';
import { MONSTERS } from '../src/data/monsters.js';
import { spawnMonsters, monsterStep } from '../src/core/rules.js';
import { newGame, act, getView } from '../src/core/game.js';

// A 12 x 5 room of floor with walls on the border. Start and stairs are fixed.
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

test('the table has an ability on every row and a new ranged kind at the end', () => {
  for (const row of MONSTERS) assert.ok(row.ability === null || typeof row.ability === 'string', row.kind);
  assert.equal(MONSTERS[MONSTERS.length - 1].kind, 'archer');
  assert.equal(MONSTERS[MONSTERS.length - 1].ability, 'ranged');
});

test('spawnMonsters copies the ability onto each monster', () => {
  const map = room();
  const occupied = new Set();
  const spawned = spawnMonsters(fixedRng, map, 5, occupied);
  assert.ok(spawned.length > 0);
  for (const m of spawned) {
    assert.equal(m.ability, MONSTERS.find((row) => row.kind === m.kind).ability, m.kind);
  }
});

test('monsterStep returns shoot only for ranged monsters at distance 2 to 4 that are visible', () => {
  const map = room(), player = { x: 2, y: 2 };
  const visible = new Set([2 * map.w + 5]);
  const far = monster({ x: 5, y: 2, ability: 'ranged' });
  assert.deepEqual(monsterStep(map, far, player, visible, () => false, fixedRng), { type: 'shoot' });
  const melee = monster({ x: 5, y: 2, ability: null });
  assert.notEqual(monsterStep(map, melee, player, visible, () => false, fixedRng).type, 'shoot');
  const hidden = monster({ x: 5, y: 2, ability: 'ranged' });
  assert.notEqual(monsterStep(map, hidden, player, new Set(), () => false, fixedRng).type, 'shoot');
});

test('a shot uses the monster attack minus 1, never below 1', () => {
  const state = newGame(4);
  const spot = [...state.visible].map((i) => ({ x: i % state.map.w, y: Math.floor(i / state.map.w) }))
    .find((c) => state.map.tiles[c.y * state.map.w + c.x] === '.' && Math.max(
      Math.abs(c.x - state.player.x), Math.abs(c.y - state.player.y)) === 3);
  assert.ok(spot, 'no visible floor tile 3 away for seed 4');
  state.monsters = [monster({ ...spot, ability: 'ranged', atk: 1 })];
  state.player.hp = 30;
  act(state, { type: 'wait' });
  assert.ok(state.log.some((line) => /^The test shoots you for \d+\.$/.test(line)), state.log.join('|'));
  const dmg = 30 - state.player.hp;
  assert.ok(dmg >= 1 && dmg <= 3, `damage ${dmg} for a monster with atk 1`);
});

test('regen heals 1 hp per monster phase and stops at maxHp', () => {
  const state = newGame(1);
  state.monsters = [monster({ ...state.map.stairs, hp: 9, maxHp: 10, atk: 0, ability: 'regen' })];
  act(state, { type: 'wait' });
  assert.equal(state.monsters[0].hp, 10);
  act(state, { type: 'wait' });
  assert.equal(state.monsters[0].hp, 10);
});

test('a poison melee hit poisons the player; the turn itself ticks it down', () => {
  const state = newGame(1);
  const { x, y } = state.player;
  state.monsters = [monster({ x: x + 1, y, hp: 5, maxHp: 5, atk: 2, ability: 'poison' })];
  state.player.hp = 30;
  act(state, { type: 'wait' });
  assert.equal(state.player.poison, 2);
  assert.equal(getView(state).hud.poison, 2);
  assert.ok(state.log.includes('Poison hurts you.'));
});

test('poison ticks on a descend turn too', () => {
  const state = newGame(1);
  state.monsters = [];
  state.player.x = state.map.stairs.x;
  state.player.y = state.map.stairs.y;
  state.player.poison = 2;
  const hp = state.player.hp;
  act(state, { type: 'descend' });
  assert.equal(state.depth, 2);
  assert.equal(state.player.hp, hp - 1);
});

test('dying from poison ends the game as an ordinary death', () => {
  const state = newGame(1);
  state.monsters = [];
  state.player.hp = 1;
  state.player.poison = 3;
  act(state, { type: 'wait' });
  assert.equal(state.status, 'dead');
  assert.equal(state.log[state.log.length - 1], 'You die.');
});

test('view hud.poison is 0 when not poisoned', () => {
  assert.equal(getView(newGame(1)).hud.poison, 0);
});

test('visibleMonsters lists living monsters on visible tiles with their fields', () => {
  const state = newGame(1);
  const spot = [...state.visible].map((i) => ({ x: i % state.map.w, y: Math.floor(i / state.map.w) }))
    .find((c) => state.map.tiles[c.y * state.map.w + c.x] === '.');
  state.monsters = [
    monster({ ...spot, kind: 'seen', ability: 'regen' }),
    monster({ id: 901, x: 0, y: 0, kind: 'hidden' }),
    monster({ id: 902, ...spot, kind: 'dead', hp: 0 }),
  ];
  const { visibleMonsters } = getView(state);
  assert.equal(visibleMonsters.length, 1);
  assert.deepEqual(Object.keys(visibleMonsters[0]).sort(),
    ['ability', 'color', 'glyph', 'hp', 'kind', 'maxHp']);
  assert.equal(visibleMonsters[0].kind, 'seen');
  assert.equal(visibleMonsters[0].ability, 'regen');
});
