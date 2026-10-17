import test from 'node:test';
import assert from 'node:assert/strict';
import { TRAPS } from '../src/data/traps.js';
import { spawnTraps, spawnMonsters, spawnItems } from '../src/core/rules.js';
import { createRng } from '../src/core/rng.js';
import { generateMap, FLOOR } from '../src/core/map.js';
import { newGame, act, getView } from '../src/core/game.js';

const DIRS = [[1, 0], [-1, 0], [0, 1], [0, -1], [1, 1], [-1, -1], [1, -1], [-1, 1]];

test('trap ids do not collide with monster or item ids on the same level', () => {
  const rng = createRng(11);
  const map = generateMap(rng);
  const occupied = new Set();
  const monsters = spawnMonsters(rng, map, 4, occupied);
  const items = spawnItems(rng, map, 4, occupied);
  const traps = spawnTraps(rng, map, 4, occupied);
  const ids = [...monsters, ...items, ...traps].map((e) => e.id);
  assert.equal(new Set(ids).size, ids.length);
});

test('a monster stepping on a trap does not reveal or fire it', () => {
  const state = newGame(5);
  state.monsters = [];
  const { x, y } = state.player;
  const [dx, dy] = DIRS.find(([dx, dy]) => state.map.tiles[(y + dy) * state.map.w + x + dx] === FLOOR);
  state.traps = [{ ...TRAPS[0], id: 9999, x: x + dx, y: y + dy, hidden: true }];
  const hp = state.player.hp;
  // A monster standing on the trap tile, next to the player, must not trigger it.
  state.monsters = [{ id: 8888, kind: 'rat', glyph: 'r', color: '#b9a37e', x: x + dx, y: y + dy,
    hp: 3, maxHp: 3, atk: 1, def: 0, xp: 1, ability: null }];
  act(state, { type: 'wait' });
  assert.equal(state.traps[0].hidden, true);
  assert.ok(state.player.hp >= hp - 1);
  assert.ok(!state.log.some((l) => l.includes('trap')));
});

test('a teleport lands on a floor tile with no monster and no trap', () => {
  for (let seed = 1; seed <= 5; seed++) {
    const state = newGame(seed);
    state.monsters = [];
    const { x, y } = state.player;
    const [dx, dy] = DIRS.find(([dx, dy]) => state.map.tiles[(y + dy) * state.map.w + x + dx] === FLOOR);
    const spot = { x: x + dx, y: y + dy };
    state.traps = [{ ...TRAPS.find((t) => t.effect === 'teleport'), id: 9999, ...spot, hidden: true }];
    act(state, { type: 'move', dx, dy });
    const p = state.player;
    assert.equal(state.map.tiles[p.y * state.map.w + p.x], FLOOR);
    assert.ok(!state.traps.some((t) => t.x === p.x && t.y === p.y));
  }
});

test('the damage trap never drops the player below 1 hp and logs the amount', () => {
  const state = newGame(9);
  state.monsters = [];
  const { x, y } = state.player;
  const [dx, dy] = DIRS.find(([dx, dy]) => state.map.tiles[(y + dy) * state.map.w + x + dx] === FLOOR);
  const row = TRAPS.find((t) => t.effect === 'damage');
  state.traps = [{ ...row, id: 9999, x: x + dx, y: y + dy, hidden: true }];
  state.player.hp = 2;
  act(state, { type: 'move', dx, dy });
  assert.equal(state.player.hp, 1);
  assert.ok(state.log.includes(`A ${row.kind} trap wounds you for 1.`));
});

test('the view lists only revealed traps on visible tiles', () => {
  const state = newGame(4);
  state.monsters = [];
  const far = state.map.rooms[state.map.rooms.length - 1];
  const i = far.y * state.map.w + far.x;
  state.traps = [{ ...TRAPS[0], id: 9999, x: far.x, y: far.y, hidden: false }];
  state.visible = new Set([state.player.y * state.map.w + state.player.x]);
  assert.deepEqual(getView(state).traps, []);
  assert.notEqual(getView(state).cells[i].ch, TRAPS[0].glyph);
});
