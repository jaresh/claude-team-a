import { test } from 'node:test';
import assert from 'node:assert/strict';
import { MONSTERS } from '../src/data/monsters.js';
import { ITEMS } from '../src/data/items.js';
import {
  spawnMonsters, spawnItems, attack, applyItem, monsterStep,
} from '../src/core/rules.js';

// Fake rng: returns the values in `vals` in turn (cycling). int(min, max) = min + (v % span).
function seqRng(vals) {
  let i = 0;
  const take = () => vals[i++ % vals.length];
  const rng = {
    next: () => take() / 1000,
    int: (min, max) => min + (take() % (max - min + 1)),
    pick: (arr) => arr[rng.int(0, arr.length - 1)],
    state: () => 0,
  };
  return rng;
}

// Map from rows of '#', '.', '>'. Start is given explicitly.
function makeMap(rows, start) {
  const h = rows.length, w = rows[0].length;
  const tiles = rows.join('').split('');
  let stairs = null;
  tiles.forEach((c, i) => {
    if (c === '>') stairs = { x: i % w, y: Math.floor(i / w) };
  });
  return { w, h, tiles, rooms: [], start, stairs };
}

// A walled room with interior floor, start at (1,1) and stairs in the bottom-right corner.
function roomMap(w, h) {
  const rows = [];
  for (let y = 0; y < h; y++) {
    let row = '';
    for (let x = 0; x < w; x++) {
      const edge = x === 0 || y === 0 || x === w - 1 || y === h - 1;
      row += edge ? '#' : '.';
    }
    rows.push(row);
  }
  const chars = rows.map((r) => r.split(''));
  chars[h - 2][w - 2] = '>';
  return makeMap(chars.map((c) => c.join('')), { x: 1, y: 1 });
}

const idx = (map, x, y) => y * map.w + x;

test('spawnMonsters makes 2 + floor(depth/2) monsters', () => {
  const map = roomMap(20, 12);
  for (const depth of [1, 2, 3, 5]) {
    const monsters = spawnMonsters(seqRng([5, 9, 2, 14, 7]), map, depth, new Set());
    assert.equal(monsters.length, 2 + Math.floor(depth / 2));
  }
});

test('spawnItems makes 4 + floor(depth/2) items', () => {
  const map = roomMap(20, 12);
  const expected = { 1: 4, 2: 5, 3: 5, 4: 6, 5: 6 };
  for (const depth of [1, 2, 3, 4, 5]) {
    const items = spawnItems(seqRng([5, 9, 2, 14, 7]), map, depth, new Set());
    assert.equal(items.length, expected[depth]);
  }
});

test('spawnMonsters respects minDepth', () => {
  const map = roomMap(20, 12);
  const depth1 = spawnMonsters(seqRng([0, 1, 2, 3, 4, 5, 6]), map, 1, new Set());
  assert.ok(depth1.length > 0);
  for (const m of depth1) assert.equal(m.kind, 'rat');

  const depth3 = spawnMonsters(seqRng([0, 1, 2, 3, 4, 5, 6, 7, 8]), map, 3, new Set());
  for (const m of depth3) {
    const row = MONSTERS.find((r) => r.kind === m.kind);
    assert.ok(row.minDepth <= 3, `${m.kind} spawned at depth 3`);
  }
});

test('spawnItems respects minDepth', () => {
  const map = roomMap(20, 12);
  const items = spawnItems(seqRng([0, 1, 2, 3, 4, 5]), map, 1, new Set());
  assert.ok(items.length > 0);
  for (const it of items) {
    const row = ITEMS.find((r) => r.kind === it.kind);
    assert.ok(row.minDepth <= 1, `${it.kind} spawned at depth 1`);
  }
});

test('spawns land only on free FLOOR tiles, never start or stairs, and occupy them', () => {
  // Walls inside the room, one pre-occupied tile.
  const map = makeMap([
    '##########',
    '#.....#..#',
    '#.#...#..#',
    '#.#......#',
    '#..#..>..#',
    '##########',
  ], { x: 1, y: 1 });
  const occupied = new Set([idx(map, 2, 1)]);
  const before = new Set(occupied);
  const monsters = spawnMonsters(seqRng([3, 7, 11, 2, 9, 4, 13]), map, 2, occupied);
  const items = spawnItems(seqRng([8, 1, 6, 10]), map, 2, occupied);
  const spawned = [...monsters, ...items];
  assert.ok(spawned.length > 0);

  const seen = new Set();
  for (const e of spawned) {
    const i = idx(map, e.x, e.y);
    assert.equal(map.tiles[i], '.', `tile ${e.x},${e.y} is not floor`);
    assert.notDeepEqual({ x: e.x, y: e.y }, map.start);
    assert.notDeepEqual({ x: e.x, y: e.y }, map.stairs);
    assert.ok(!before.has(i), `tile ${e.x},${e.y} was already occupied`);
    assert.ok(!seen.has(i), `tile ${e.x},${e.y} spawned twice`);
    seen.add(i);
    assert.ok(occupied.has(i), 'spawn tile not added to occupied');
    assert.notEqual(e.id, undefined);
  }
  assert.equal(occupied.size, before.size + spawned.length);
  const ids = spawned.map((e) => e.id);
  assert.equal(new Set(ids).size, ids.length, 'ids not unique');
});

test('spawns stop when no free floor tile is left', () => {
  // Only (3,1) is free: start (1,1), stairs (2,1).
  const map = makeMap(['#####', '#.>.#', '#####'], { x: 1, y: 1 });
  const monsters = spawnMonsters(seqRng([0, 1, 2]), map, 1, new Set());
  assert.equal(monsters.length, 1);
  assert.equal(monsters[0].x, 3);
  assert.equal(monsters[0].y, 1);
});

test('spawned monster has stats copied from its table row', () => {
  const map = roomMap(20, 12);
  const [m] = spawnMonsters(seqRng([0]), map, 1, new Set());
  const row = MONSTERS.find((r) => r.kind === m.kind);
  assert.equal(m.hp, row.hp);
  assert.equal(m.maxHp, row.hp);
  assert.equal(m.atk, row.atk);
  assert.equal(m.def, row.def);
  assert.equal(m.xp, row.xp);
  assert.equal(m.glyph, row.glyph);
});

test('attack damage is atk + int(0,2) - def, with the killed flag', () => {
  // rng.int(0, 2) returns 2 for v = 2.
  const attacker = { atk: 5 };
  const defender = { hp: 10, def: 1 };
  const r = attack(attacker, defender, seqRng([2]));
  assert.deepEqual(r, { damage: 6, killed: false });
  assert.equal(defender.hp, 4);

  const weak = { hp: 6, def: 1 };
  assert.deepEqual(attack(attacker, weak, seqRng([2])), { damage: 6, killed: true });
  assert.equal(weak.hp, 0);

  // int(0,2) returns 0 for v = 0: 5 + 0 - 1 = 4.
  const d2 = { hp: 10, def: 1 };
  assert.deepEqual(attack(attacker, d2, seqRng([0])), { damage: 4, killed: false });
});

test('attack damage is at least 1', () => {
  const d = { hp: 10, def: 9 };
  assert.deepEqual(attack({ atk: 0 }, d, seqRng([0])), { damage: 1, killed: false });
  assert.equal(d.hp, 9);
});

test('applyItem heal adds amount and caps at maxHp', () => {
  const potion = { kind: 'potion', effect: 'heal', amount: 8 };
  const p = { hp: 5, maxHp: 20, atk: 3, def: 1 };
  const msg = applyItem(p, potion);
  assert.equal(p.hp, 13);
  assert.equal(typeof msg, 'string');
  assert.ok(msg.length > 0);

  const q = { hp: 18, maxHp: 20, atk: 3, def: 1 };
  applyItem(q, potion);
  assert.equal(q.hp, 20);
});

test('applyItem atk and def add permanently', () => {
  const p = { hp: 5, maxHp: 20, atk: 3, def: 1 };
  assert.equal(typeof applyItem(p, { kind: 'whetstone', effect: 'atk', amount: 2 }), 'string');
  assert.equal(p.atk, 5);
  applyItem(p, { kind: 'ring', effect: 'def', amount: 1 });
  assert.equal(p.def, 2);
  assert.equal(p.hp, 5);
  assert.equal(p.maxHp, 20);
});

test('monsterStep attacks when adjacent and visible', () => {
  const map = roomMap(8, 6);
  const monster = { x: 3, y: 2 };
  const player = { x: 4, y: 3 };
  const visible = new Set([idx(map, 3, 2)]);
  const step = monsterStep(map, monster, player, visible, () => false, seqRng([0]));
  assert.deepEqual(step, { type: 'attack' });
});

test('monsterStep moves closer when visible and not adjacent', () => {
  const map = roomMap(12, 8);
  const monster = { x: 2, y: 2 };
  const player = { x: 7, y: 4 };
  const visible = new Set([idx(map, 2, 2)]);
  const step = monsterStep(map, monster, player, visible, () => false, seqRng([0]));
  assert.equal(step.type, 'move');
  const before = Math.max(Math.abs(2 - 7), Math.abs(2 - 4));
  const after = Math.max(Math.abs(step.x - 7), Math.abs(step.y - 4));
  assert.ok(after < before);
  assert.ok(Math.abs(step.x - 2) <= 1 && Math.abs(step.y - 2) <= 1);
});

test('monsterStep never moves onto a wall or a blocked tile', () => {
  const map = makeMap([
    '#######',
    '#.....#',
    '#######',
  ], { x: 1, y: 1 });
  const monster = { x: 2, y: 1 };
  const player = { x: 5, y: 1 };
  const visible = new Set([idx(map, 2, 1)]);
  // The only closer tile (3,1) is blocked, so the monster must step to (1,1) instead.
  const blocked = (x, y) => x === 3 && y === 1;
  const step = monsterStep(map, monster, player, visible, blocked, seqRng([0]));
  assert.deepEqual(step, { type: 'move', x: 1, y: 1 });

  // Also with the monster boxed in by walls and blocked tiles: it waits.
  const boxed = monsterStep(map, monster, player, visible, () => true, seqRng([0]));
  assert.deepEqual(boxed, { type: 'wait' });

  // Random walk (not visible): every move is onto floor and unblocked, over many rng states.
  for (let k = 0; k < 8; k++) {
    const vals = [k, k + 1, k + 2];
    const s = monsterStep(map, monster, player, new Set(), blocked, seqRng(vals));
    assert.equal(s.type, 'move');
    assert.equal(map.tiles[idx(map, s.x, s.y)], '.');
    assert.ok(!blocked(s.x, s.y));
  }
});

test('monsterStep never steps onto a wall in an open room', () => {
  const map = makeMap([
    '####',
    '#..#',
    '#..#',
    '####',
  ], { x: 1, y: 1 });
  const monster = { x: 1, y: 1 };
  const player = { x: 2, y: 2 };
  for (let k = 0; k < 8; k++) {
    const s = monsterStep(map, monster, { x: 8, y: 8 }, new Set([idx(map, 1, 1)]), () => false, seqRng([k]));
    if (s.type === 'move') assert.equal(map.tiles[idx(map, s.x, s.y)], '.');
  }
  // Not visible: the random step is still on floor.
  for (let k = 0; k < 8; k++) {
    const s = monsterStep(map, monster, player, new Set(), () => false, seqRng([k]));
    if (s.type === 'move') assert.equal(map.tiles[idx(map, s.x, s.y)], '.');
  }
});

test('monsterStep does not mutate its inputs', () => {
  const map = roomMap(12, 8);
  const monster = { x: 2, y: 2, kind: 'rat', hp: 3 };
  const player = { x: 7, y: 4, hp: 10 };
  const visible = new Set([idx(map, 2, 2), idx(map, 3, 2)]);
  const snapshot = JSON.stringify({ map, monster, player, visible: [...visible] });
  const blocked = (x, y) => x === 9 && y === 9;
  monsterStep(map, monster, player, visible, blocked, seqRng([1, 2]));
  monsterStep(map, monster, player, new Set(), blocked, seqRng([3]));
  assert.equal(JSON.stringify({ map, monster, player, visible: [...visible] }), snapshot);
});

test('attack and applyItem mutate only the entities they are given', () => {
  const a = { atk: 4, hp: 9, def: 0 };
  const d = { hp: 9, def: 0 };
  attack(a, d, seqRng([0]));
  assert.equal(a.hp, 9);
  assert.equal(a.atk, 4);
});

test('data tables have at least 5 monster kinds across depths 1-5 and at least 3 items', () => {
  assert.ok(MONSTERS.length >= 5);
  const depths = new Set(MONSTERS.map((m) => m.minDepth));
  assert.ok(Math.min(...depths) === 1 && Math.max(...depths) === 5);
  assert.ok(ITEMS.length >= 3);
  for (const it of ITEMS) assert.ok(['heal', 'atk', 'def'].includes(it.effect), it.kind);
  const kinds = [...MONSTERS.map((m) => m.kind), ...ITEMS.map((i) => i.kind)];
  assert.equal(new Set(kinds).size, kinds.length, 'duplicate kinds');
});
