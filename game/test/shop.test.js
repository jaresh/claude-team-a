import { test } from 'node:test';
import assert from 'node:assert/strict';
import { SHOP_STOCK, goldFor } from '../src/data/shop.js';
import { MONSTERS } from '../src/data/monsters.js';
import { newGame, act, getView, MAX_DEPTH } from '../src/core/game.js';

const DIRS = [[1, 0], [-1, 0], [0, 1], [0, -1]];

// A game with no monsters, standing on the start tile.
function quiet(seed = 3) {
  const s = newGame(seed);
  s.monsters = [];
  return s;
}

// Steps the player onto a walkable neighbour of the current tile.
function stepOff(s) {
  const [dx, dy] = DIRS.find(([a, b]) => s.map.tiles[(s.player.y + b) * s.map.w + s.player.x + a] === '.');
  act(s, { type: 'move', dx, dy });
}

test('goldFor is max(1, xp) * 2 + depth', () => {
  const rat = MONSTERS[0];
  assert.equal(goldFor(rat, 1), 1 * 2 + 1);
  assert.equal(goldFor({ ...rat, xp: 0 }, 3), 1 * 2 + 3);
  assert.equal(goldFor({ ...rat, xp: 15 }, 5), 15 * 2 + 5);
});

test('shop table rows are unique by kind and priced in table order', () => {
  const kinds = SHOP_STOCK.map((r) => r.kind);
  assert.equal(new Set(kinds).size, kinds.length);
  for (const r of SHOP_STOCK) assert.ok(r.amount > 0, r.kind);
});

test('stock at depth 1 is only the minDepth 1 rows, in table order', () => {
  const s = quiet();
  const stock = getView(s).shop.stock;
  const expected = SHOP_STOCK.filter((r) => r.minDepth <= 1).map((r) => r.kind);
  assert.deepEqual(stock.map((r) => r.kind), expected);
  assert.deepEqual(stock.map((r) => r.index), expected.map((_, i) => i));
});

test('stock grows with depth; the index refers to the current stock list', () => {
  const s = quiet();
  s.depth = MAX_DEPTH - 1;
  const stock = getView(s).shop.stock;
  const expected = SHOP_STOCK.filter((r) => r.minDepth <= s.depth);
  assert.equal(stock.length, expected.length);
  const last = stock[stock.length - 1];
  assert.equal(last.kind, expected[expected.length - 1].kind);
  assert.equal(last.index, expected.length - 1);
  s.player.gold = 999;
  act(s, { type: 'buy', index: last.index });
  assert.equal(s.player.inventory.at(-1).kind, expected[expected.length - 1].kind);
});

test('buying a row copies its item fields and charges its price', () => {
  const s = quiet();
  s.player.gold = 100;
  const row = SHOP_STOCK[1];
  act(s, { type: 'buy', index: 1 });
  const item = s.player.inventory.at(-1);
  assert.equal(item.kind, row.kind);
  assert.equal(item.glyph, row.glyph);
  assert.equal(item.color, row.color);
  assert.equal(item.effect, row.effect);
  assert.equal(item.amount, row.amount);
  assert.equal(item.x, 0);
  assert.equal(item.y, 0);
  assert.equal(s.player.gold, 100 - row.price);
  assert.equal(s.log.at(-1), `You buy a ${row.kind}.`);
});

test('bought item ids are negative and unique within the inventory', () => {
  const s = quiet();
  s.player.gold = 1000;
  act(s, { type: 'buy', index: 0 });
  act(s, { type: 'buy', index: 0 });
  const [a, b] = s.player.inventory;
  assert.ok(a.id < 0 && b.id < 0);
  assert.notEqual(a.id, b.id);
});

test('not enough gold logs the price and changes nothing', () => {
  const s = quiet();
  const row = SHOP_STOCK[0];
  s.player.gold = row.price - 1;
  act(s, { type: 'buy', index: 0 });
  assert.equal(s.player.gold, row.price - 1);
  assert.equal(s.player.inventory.length, 0);
  assert.equal(s.log.at(-1), `You need ${row.price} gold.`);
});

test('buying away from the shop logs a reason and changes nothing', () => {
  const s = quiet();
  stepOff(s);
  s.player.gold = 100;
  const turn = s.turn;
  act(s, { type: 'buy', index: 0 });
  assert.equal(s.log.at(-1), 'There is no shop here.');
  assert.equal(s.player.gold, 100);
  assert.equal(s.turn, turn);
});

test('a bad index logs a reason and changes nothing', () => {
  const s = quiet();
  s.player.gold = 100;
  act(s, { type: 'buy', index: 1.5 });
  act(s, { type: 'buy', index: 'x' });
  assert.equal(s.log.at(-1), 'Nothing like that is for sale.');
  assert.equal(s.player.inventory.length, 0);
  assert.equal(s.player.gold, 100);
});

test('a bought potion can be used like any other item', () => {
  const s = quiet();
  s.player.gold = 100;
  s.player.hp = 5;
  act(s, { type: 'buy', index: 0 });
  act(s, { type: 'use', index: 0 });
  assert.equal(s.player.inventory.length, 0);
  assert.ok(s.player.hp > 5);
});

test('view shop: open with stock on the start tile, closed and empty elsewhere', () => {
  const s = quiet();
  const v = getView(s);
  assert.equal(v.shop.open, true);
  assert.equal(v.shop.x, s.map.start.x);
  assert.equal(v.shop.y, s.map.start.y);
  stepOff(s);
  const away = getView(s);
  assert.equal(away.shop.open, false);
  assert.deepEqual(away.shop.stock, []);
});

test('hud.gold drops by the price of a purchase', () => {
  const s = quiet();
  s.player.gold = 20;
  act(s, { type: 'buy', index: 0 });
  assert.equal(getView(s).hud.gold, 20 - SHOP_STOCK[0].price);
});

test('shop tile shows $ when visible and dim $ when only explored', () => {
  const s = quiet();
  stepOff(s);
  const i = s.map.start.y * s.map.w + s.map.start.x;
  const v = getView(s);
  assert.equal(v.cells[i].ch, '$');
  assert.equal(v.cells[i].fg, '#fbbf24', 'visible shop is gold');
  s.visible.delete(i);
  const dim = getView(s).cells[i];
  assert.equal(dim.ch, '$');
  assert.notEqual(dim.fg, '#fbbf24');
});

test('the shop does not show over the player standing on it', () => {
  const s = quiet();
  const v = getView(s);
  const i = s.map.start.y * s.map.w + s.map.start.x;
  assert.equal(v.cells[i].ch, s.player.glyph);
});

test('gold stays with the player on descend', () => {
  const s = quiet();
  s.player.gold = 42;
  s.player.x = s.map.stairs.x;
  s.player.y = s.map.stairs.y;
  act(s, { type: 'descend' });
  assert.equal(s.depth, 2);
  assert.equal(s.player.gold, 42);
  assert.equal(getView(s).shop.open, true);
});
