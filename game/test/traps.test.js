import { test } from 'node:test';
import assert from 'node:assert/strict';
import { TRAPS } from '../src/data/traps.js';
import { spawnTraps, spawnMonsters, spawnItems } from '../src/core/rules.js';
import { createRng } from '../src/core/rng.js';
import { generateMap, isWalkable, FLOOR } from '../src/core/map.js';
import { newGame, act, getView } from '../src/core/game.js';

const DIRS = [[1, 0], [-1, 0], [0, 1], [0, -1]];

// A new game with no monsters and no items, and one trap of `row` on the tile east or west
// of the player (whichever is floor). The trap is hidden unless `hidden` says otherwise.
function setupWith(row, hidden = true) {
  const state = newGame(11);
  state.monsters = [];
  state.items = [];
  const { x, y } = state.player;
  const [dx, dy] = DIRS.find(([dx, dy]) => isWalkable(state.map, x + dx, y + dy)
    && state.map.tiles[(y + dy) * state.map.w + x + dx] === FLOOR);
  const spot = { x: x + dx, y: y + dy };
  state.traps = [{ ...row, id: 500, x: spot.x, y: spot.y, hidden }];
  return { state, spot, dx, dy };
}

// Some floor tile that is not the player's, not `spot` and not the stairs.
function floorTileOtherThan(state, spot) {
  const { map, player } = state;
  for (let i = 0; i < map.tiles.length; i++) {
    const x = i % map.w, y = Math.floor(i / map.w);
    if (map.tiles[i] === FLOOR && !(x === spot.x && y === spot.y) && !(x === player.x && y === player.y)) {
      return { x, y };
    }
  }
  return null;
}

test('every trap row has a known effect and a glyph and colour', () => {
  for (const t of TRAPS) {
    assert.ok(['damage', 'poison', 'teleport'].includes(t.effect), t.kind);
    assert.equal(typeof t.glyph, 'string', t.kind);
    assert.match(t.color, /^#[0-9a-f]{6}$/i, t.kind);
    assert.ok(Number.isInteger(t.minDepth), t.kind);
  }
  assert.equal(new Set(TRAPS.map((t) => t.kind)).size, TRAPS.length);
});

test('spawnTraps only uses kinds whose minDepth is reached', () => {
  const rng = createRng(5);
  const map = generateMap(rng);
  const traps = spawnTraps(rng, map, 1, new Set());
  assert.equal(traps.length, 2);
  for (const t of traps) assert.equal(t.kind, 'spike');
});

test('trap ids never collide with monster or item ids on the same level', () => {
  for (let seed = 1; seed <= 20; seed++) {
    const rng = createRng(seed);
    const map = generateMap(rng);
    const occupied = new Set();
    const ids = [
      ...spawnMonsters(rng, map, 5, occupied),
      ...spawnItems(rng, map, 5, occupied),
      ...spawnTraps(rng, map, 5, occupied),
    ].map((e) => e.id);
    assert.equal(new Set(ids).size, ids.length, `seed ${seed}`);
  }
});

test('a monster stepping onto a trap does not trigger it', () => {
  const { state, spot, dx, dy } = setupWith(TRAPS[0]);
  // The monster starts two tiles from the player, so its next step is onto the trap tile.
  const far = { x: spot.x + dx, y: spot.y + dy };
  assert.equal(state.map.tiles[far.y * state.map.w + far.x], FLOOR);
  const m = { id: 900, kind: 'rat', glyph: 'r', color: '#ffffff', x: far.x, y: far.y, hp: 3,
    maxHp: 3, atk: 1, def: 0, xp: 0, ability: null };
  state.monsters = [m];
  act(state, { type: 'wait' });
  assert.deepEqual([m.x, m.y], [spot.x, spot.y]);
  assert.equal(state.traps[0].hidden, true);
  assert.ok(!state.log.some((l) => l.includes('trap')));
});

test('a trap shows in the view only once it is revealed and the tile is visible', () => {
  const { state, spot } = setupWith(TRAPS[0], false);
  const i = spot.y * state.map.w + spot.x;
  assert.equal(getView(state).cells[i].ch, TRAPS[0].glyph);
  assert.deepEqual(getView(state).traps, [
    { kind: 'spike', glyph: '^', color: TRAPS[0].color, x: spot.x, y: spot.y },
  ]);
  state.traps[0].hidden = true;
  assert.deepEqual(getView(state).traps, []);
});

test('a damage trap that fires at 1 hp logs the hp it actually took', () => {
  const { state, dx, dy } = setupWith(TRAPS[0]);
  state.player.hp = 2;
  act(state, { type: 'move', dx, dy });
  assert.equal(state.player.hp, 1);
  assert.ok(state.log.includes('A spike trap wounds you for 1.'));
});

test('a poison trap poisons the player, and the poison ticks that turn', () => {
  const { state, dx, dy } = setupWith(TRAPS.find((t) => t.effect === 'poison'));
  const hp = state.player.hp;
  act(state, { type: 'move', dx, dy });
  assert.equal(state.player.poison, 2);
  assert.equal(state.player.hp, hp - 1);
});

test('a teleport trap lands on floor with no monster and no trap', () => {
  const row = TRAPS.find((t) => t.effect === 'teleport');
  for (let seed = 1; seed <= 10; seed++) {
    const { state, spot, dx, dy } = setupWith(row);
    state.rngState = seed;
    const other = floorTileOtherThan(state, spot);
    state.traps.push({ ...row, id: 501, ...other, hidden: true });
    act(state, { type: 'move', dx, dy });
    const p = state.player;
    assert.equal(state.map.tiles[p.y * state.map.w + p.x], FLOOR);
    assert.ok(!(p.x === spot.x && p.y === spot.y), `seed ${seed}`);
    assert.ok(!(p.x === other.x && p.y === other.y), `seed ${seed}`);
  }
});

test('descend builds traps on the new level and clears the old ones', () => {
  const state = newGame(3);
  state.player.x = state.map.stairs.x;
  state.player.y = state.map.stairs.y;
  const old = state.traps;
  act(state, { type: 'descend' });
  assert.notEqual(state.traps, old);
  assert.equal(state.traps.length, 3);
});
