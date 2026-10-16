import { test } from 'node:test';
import assert from 'node:assert/strict';
import { newGame, act, getView, MAX_DEPTH } from '../src/core/game.js';
import { createRng } from '../src/core/rng.js';
import { WALL, FLOOR } from '../src/core/map.js';

const idx = (s, x, y) => y * s.map.w + x;

// Plain-data snapshot for determinism checks (Set -> array).
function snapshot(s) {
  return JSON.stringify({ ...s, visible: [...s.visible] });
}

function rat(s, x, y, extra = {}) {
  return {
    id: 900 + x + y * 100, kind: 'rat', glyph: 'r', color: '#fff', x, y,
    hp: 3, maxHp: 3, atk: 1, def: 0, xp: 1, ...extra,
  };
}

// Start tile is the centre of the first room, so all 8 neighbours are floor.
function clearMonsters(s) {
  s.monsters = [];
  s.items = [];
}

test('newGame is deterministic, starts on map.start, status playing', () => {
  const a = newGame(7);
  const b = newGame(7);
  assert.equal(snapshot(a), snapshot(b));
  assert.equal(a.status, 'playing');
  assert.equal(a.turn, 0);
  assert.equal(a.depth, 1);
  assert.equal(a.player.x, a.map.start.x);
  assert.equal(a.player.y, a.map.start.y);
  assert.notEqual(snapshot(newGame(8)), snapshot(a));
});

test('newGame accepts string seeds deterministically', () => {
  assert.equal(snapshot(newGame('dungeon')), snapshot(newGame('dungeon')));
});

test('moving into a wall costs no turn', () => {
  const s = newGame(3);
  clearMonsters(s);
  // Find a floor tile with a wall next to it.
  let spot = null;
  for (let y = 1; y < s.map.h - 1 && !spot; y++) {
    for (let x = 1; x < s.map.w - 1 && !spot; x++) {
      if (s.map.tiles[idx(s, x, y)] !== FLOOR) continue;
      if (s.map.tiles[idx(s, x - 1, y)] === WALL) spot = { x, y, dx: -1, dy: 0 };
    }
  }
  assert.ok(spot, 'map has a floor tile next to a wall');
  s.player.x = spot.x;
  s.player.y = spot.y;
  act(s, { type: 'move', dx: spot.dx, dy: spot.dy });
  assert.equal(s.turn, 0);
  assert.equal(s.player.x, spot.x);
  assert.equal(s.player.y, spot.y);
  assert.equal(s.status, 'playing');
});

test('moving into a monster attacks it and does not move the player', () => {
  const s = newGame(5);
  clearMonsters(s);
  const { x, y } = s.map.start;
  s.monsters = [rat(s, x + 1, y, { hp: 100 })];
  act(s, { type: 'move', dx: 1, dy: 0 });
  assert.equal(s.monsters.length, 1);
  assert.ok(s.monsters[0].hp < 100, 'monster took damage');
  assert.equal(s.player.x, x);
  assert.equal(s.turn, 1);
});

test('killing a monster removes it and adds xp', () => {
  const s = newGame(5);
  clearMonsters(s);
  const { x, y } = s.map.start;
  s.monsters = [rat(s, x + 1, y, { hp: 1, xp: 4 })];
  act(s, { type: 'move', dx: 1, dy: 0 });
  assert.equal(s.monsters.length, 0);
  assert.equal(s.player.xp, 4);
  assert.equal(s.player.level, 1);
});

test('10 xp levels up: +5 maxHp, +1 atk', () => {
  const s = newGame(5);
  clearMonsters(s);
  const { x, y } = s.map.start;
  s.player.xp = 8;
  const maxHp = s.player.maxHp, atk = s.player.atk;
  s.monsters = [rat(s, x + 1, y, { hp: 1, xp: 2 })];
  act(s, { type: 'move', dx: 1, dy: 0 });
  assert.equal(s.player.xp, 10);
  assert.equal(s.player.level, 2);
  assert.equal(s.player.maxHp, maxHp + 5);
  assert.equal(s.player.atk, atk + 1);
});

test('pickup and use an item', () => {
  const s = newGame(9);
  clearMonsters(s);
  const { x, y } = s.map.start;
  s.items = [{ id: 77, kind: 'potion', glyph: '!', color: '#f0f', effect: 'heal', amount: 8, x, y }];
  act(s, { type: 'pickup' });
  assert.equal(s.items.length, 0);
  assert.equal(s.player.inventory.length, 1);
  assert.equal(s.turn, 1);

  s.player.hp = 5;
  act(s, { type: 'use', index: 0 });
  assert.equal(s.player.hp, 13);
  assert.equal(s.player.inventory.length, 0);
  assert.equal(s.turn, 2);
});

test('pickup with nothing here and use of an empty slot cost no turn', () => {
  const s = newGame(9);
  clearMonsters(s);
  act(s, { type: 'pickup' });
  act(s, { type: 'use', index: 0 });
  act(s, { type: 'use', index: -1 });
  assert.equal(s.turn, 0);
});

test('descend works only on stairs and keeps stats and inventory', () => {
  const s = newGame(11);
  clearMonsters(s);
  act(s, { type: 'descend' });
  assert.equal(s.depth, 1);
  assert.equal(s.turn, 0);

  s.player.x = s.map.stairs.x;
  s.player.y = s.map.stairs.y;
  s.player.hp = 7;
  s.player.atk = 5;
  s.player.def = 2;
  s.player.xp = 3;
  s.player.inventory = [{ id: 1, kind: 'potion', glyph: '!', color: '#f0f', effect: 'heal', amount: 8 }];
  act(s, { type: 'descend' });
  assert.equal(s.depth, 2);
  assert.equal(s.status, 'playing');
  assert.equal(s.player.hp, 7);
  assert.equal(s.player.atk, 5);
  assert.equal(s.player.def, 2);
  assert.equal(s.player.xp, 3);
  assert.equal(s.player.inventory.length, 1);
  assert.equal(s.player.inventory[0].kind, 'potion');
  assert.equal(s.player.x, s.map.start.x);
  assert.equal(s.player.y, s.map.start.y);
});

test('descend on MAX_DEPTH sets status won, and later actions are ignored', () => {
  const s = newGame(11);
  s.depth = MAX_DEPTH;
  s.player.x = s.map.stairs.x;
  s.player.y = s.map.stairs.y;
  act(s, { type: 'descend' });
  assert.equal(s.status, 'won');
  const turn = s.turn;
  act(s, { type: 'wait' });
  assert.equal(s.turn, turn);
});

test('hp at 0 or below sets status dead, and later actions are ignored', () => {
  const s = newGame(13);
  clearMonsters(s);
  s.player.hp = 0;
  act(s, { type: 'wait' });
  assert.equal(s.status, 'dead');

  const turn = s.turn;
  const { x, y } = s.player;
  act(s, { type: 'move', dx: 1, dy: 0 });
  act(s, { type: 'wait' });
  assert.equal(s.turn, turn);
  assert.equal(s.player.x, x);
  assert.equal(s.player.y, y);
});

test('a monster can kill the player during the monster phase', () => {
  const s = newGame(13);
  clearMonsters(s);
  const { x, y } = s.map.start;
  s.player.hp = 1;
  s.monsters = [rat(s, x + 1, y, { atk: 50 })];
  act(s, { type: 'wait' });
  assert.equal(s.status, 'dead');
  assert.equal(getView(s).status, 'dead');
});

test('getView returns w*h cells, player glyph on the player tile, blank unexplored tiles', () => {
  const s = newGame(21);
  const v = getView(s);
  assert.equal(v.w, s.map.w);
  assert.equal(v.h, s.map.h);
  assert.equal(v.cells.length, v.w * v.h);
  const p = s.player;
  assert.equal(v.cells[idx(s, p.x, p.y)].ch, '@');
  let blank = 0;
  for (let i = 0; i < s.map.w * s.map.h; i++) {
    if (!s.explored[i]) {
      assert.equal(v.cells[i].ch, ' ');
      blank++;
    }
  }
  assert.ok(blank > 0, 'some tiles are unexplored');
  assert.equal(v.hud.depth, 1);
  assert.equal(v.status, 'playing');
});

test('getView returns at most 5 log lines', () => {
  const s = newGame(21);
  for (let i = 0; i < 10; i++) s.log.push(`line ${i}`);
  const v = getView(s);
  assert.equal(v.log.length, 5);
  assert.equal(v.log[4], 'line 9');
});

test('visible tiles are never blank in getView', () => {
  const s = newGame(21);
  const v = getView(s);
  for (const i of s.visible) assert.notEqual(v.cells[i].ch, ' ');
});

test('a 200-turn random walk on 5 seeds never throws', () => {
  for (const seed of [1, 2, 3, 4, 5]) {
    const s = newGame(seed);
    const pick = createRng(seed + 1000);
    for (let t = 0; t < 200; t++) {
      const r = pick.int(0, 19);
      let action;
      if (r < 10) action = { type: 'move', dx: pick.int(-1, 1), dy: pick.int(-1, 1) };
      else if (r < 13) action = { type: 'wait' };
      else if (r < 15) action = { type: 'pickup' };
      else if (r < 17) action = { type: 'use', index: pick.int(0, 2) };
      else action = { type: 'descend' };
      act(s, action);
      getView(s);
    }
    assert.ok(['playing', 'dead', 'won'].includes(s.status));
  }
});
