// Acceptance test for run e6 (lead-owned; teammates do not edit it).
import test from 'node:test';
import assert from 'node:assert/strict';
import { SHOP_STOCK, goldFor } from '../src/data/shop.js';
import { MONSTERS } from '../src/data/monsters.js';
import { newGame, act, getView } from '../src/core/game.js';

function quiet(seed = 3) {
  const s = newGame(seed);
  s.monsters = [];
  return s;
}

test('shop table', () => {
  assert.ok(SHOP_STOCK.length >= 3);
  for (const r of SHOP_STOCK) {
    for (const k of ['kind', 'glyph', 'color', 'effect', 'amount', 'price', 'minDepth']) assert.ok(k in r, `${r.kind}.${k}`);
    assert.ok(['heal', 'atk', 'def'].includes(r.effect));
    assert.ok(Number.isInteger(r.price) && r.price > 0);
  }
  assert.ok(SHOP_STOCK.some((r) => r.minDepth === 1));
});

test('goldFor is a positive integer per monster and depth, no randomness', () => {
  for (const m of MONSTERS) assert.ok(Number.isInteger(goldFor(m, 1)) && goldFor(m, 1) >= 1);
  assert.equal(goldFor(MONSTERS[0], 2), goldFor(MONSTERS[0], 2));
});

test('player starts with 0 gold; killing a monster gives goldFor', () => {
  const s = quiet();
  assert.equal(getView(s).hud.gold, 0);
  const p = s.player;
  const m = { ...MONSTERS[0], id: 900, maxHp: 1, hp: 1, x: p.x + 1, y: p.y, ability: null };
  s.map.tiles = s.map.tiles.slice();
  s.monsters = [m];
  p.atk = 50;
  // clear the tile east (make sure walkable) by trying all directions
  const dirs = [[1, 0], [-1, 0], [0, 1], [0, -1]];
  const [dx, dy] = dirs.find(([a, b]) => s.map.tiles[(p.y + b) * s.map.w + p.x + a] === '.');
  m.x = p.x + dx; m.y = p.y + dy;
  act(s, { type: 'move', dx, dy });
  assert.equal(s.monsters.length, 0);
  assert.equal(getView(s).hud.gold, goldFor(MONSTERS[0], 1));
});

test('shop is at the start tile: view.shop lists stock only while standing there', () => {
  const s = quiet();
  const v = getView(s);
  assert.ok(v.shop && v.shop.x === s.map.start.x && v.shop.y === s.map.start.y);
  assert.equal(v.shop.open, true);
  assert.ok(v.shop.stock.length >= 1);
  for (const r of v.shop.stock) for (const k of ['index', 'kind', 'glyph', 'color', 'price']) assert.ok(k in r);
  const dirs = [[1, 0], [-1, 0], [0, 1], [0, -1]];
  const [dx, dy] = dirs.find(([a, b]) => s.map.tiles[(s.player.y + b) * s.map.w + s.player.x + a] === '.');
  act(s, { type: 'move', dx, dy });
  const v2 = getView(s);
  assert.equal(v2.shop.open, false);
  assert.deepEqual(v2.shop.stock, []);
  assert.deepEqual([v2.shop.x, v2.shop.y], [s.map.start.x, s.map.start.y]);
});

test('buy: needs gold and the shop tile; adds item, costs gold, takes no turn', () => {
  const s = quiet();
  const row = SHOP_STOCK.find((r) => r.minDepth <= 1);
  const idx = getView(s).shop.stock.find((r) => r.kind === row.kind).index;
  let turn = s.turn;
  act(s, { type: 'buy', index: idx });
  assert.equal(s.player.inventory.length, 0, 'no gold, no item');
  assert.equal(s.turn, turn);
  s.player.gold = row.price + 3;
  act(s, { type: 'buy', index: idx });
  assert.equal(s.player.inventory.length, 1);
  assert.equal(s.player.inventory[0].kind, row.kind);
  assert.equal(s.player.inventory[0].effect, row.effect);
  assert.equal(getView(s).hud.gold, 3);
  assert.equal(s.turn, turn, 'buying takes no turn');
  assert.equal(getView(s).inventory[0].kind, row.kind);
  // stock is unlimited
  s.player.gold = row.price;
  act(s, { type: 'buy', index: idx });
  assert.equal(s.player.inventory.length, 2);
  // bad index ignored
  s.player.gold = 999;
  act(s, { type: 'buy', index: 99 });
  act(s, { type: 'buy', index: -1 });
  assert.equal(s.player.inventory.length, 2);
  assert.equal(s.player.gold, 999);
});

test('buy away from the shop tile does nothing', () => {
  const s = quiet();
  const dirs = [[1, 0], [-1, 0], [0, 1], [0, -1]];
  const [dx, dy] = dirs.find(([a, b]) => s.map.tiles[(s.player.y + b) * s.map.w + s.player.x + a] === '.');
  act(s, { type: 'move', dx, dy });
  s.player.gold = 100;
  act(s, { type: 'buy', index: 0 });
  assert.equal(s.player.inventory.length, 0);
  assert.equal(s.player.gold, 100);
});

test('every level has a shop; gold persists on descend; stock respects minDepth', () => {
  const s = quiet();
  s.player.gold = 42;
  s.player.x = s.map.stairs.x; s.player.y = s.map.stairs.y;
  act(s, { type: 'descend' });
  assert.equal(s.depth, 2);
  assert.equal(s.player.gold, 42);
  const v = getView(s);
  assert.ok(v.shop.open);
  for (const r of v.shop.stock) assert.ok(SHOP_STOCK.find((x) => x.kind === r.kind).minDepth <= 2);
});

test('view shop cell shows $ on the shop tile when the player is elsewhere', () => {
  const s = quiet();
  const dirs = [[1, 0], [-1, 0], [0, 1], [0, -1]];
  const [dx, dy] = dirs.find(([a, b]) => s.map.tiles[(s.player.y + b) * s.map.w + s.player.x + a] === '.');
  act(s, { type: 'move', dx, dy });
  const v = getView(s);
  assert.equal(v.cells[s.map.start.y * v.w + s.map.start.x].ch, '$');
});
