import { test } from 'node:test';
import assert from 'node:assert/strict';
import { newGame, getView } from '../src/ui/mock-game.js';
import { shopRows } from '../src/ui/render.js';
import { bindInput, buttonToAction } from '../src/ui/input.js';

const stockRow = (index, kind, price) => ({
  index, kind, glyph: '!', color: '#ff5fa2', effect: 'heal', amount: 8, price,
});

test('shopRows: nothing while the shop is not open', () => {
  assert.deepEqual(shopRows({ x: 3, y: 3, open: false, stock: [] }), []);
  assert.deepEqual(shopRows(undefined), []);
});

test('shopRows: one row per stock entry, keeping the stock index that buy takes', () => {
  const shop = {
    x: 3, y: 3, open: true,
    stock: [stockRow(0, 'potion', 5), stockRow(2, 'shield', 9)],
  };
  assert.deepEqual(shopRows(shop), [
    { index: 0, text: '! potion 5g' },
    { index: 2, text: '! shield 9g' },
  ]);
});

test('buttonToAction: a shop button carries data-index and becomes a buy action', () => {
  assert.deepEqual(buttonToAction({ action: 'buy', index: '0' }), { type: 'buy', index: 0 });
  assert.deepEqual(buttonToAction({ action: 'buy', index: '2' }), { type: 'buy', index: 2 });
});

test('buttonToAction: a shop button without a usable index is not an action', () => {
  assert.equal(buttonToAction({ action: 'buy' }), null);
  assert.equal(buttonToAction({ action: 'buy', index: 'x' }), null);
});

test('bindInput: a tap on a buy button reaches onAction as a buy action', () => {
  const handlers = {};
  const btn = { dataset: { action: 'buy', index: '1' } };
  const root = {
    addEventListener: (type, fn) => { handlers[type] = fn; },
    removeEventListener: () => {},
    contains: (el) => el === btn,
  };
  const actions = [];
  bindInput(root, (a) => actions.push(a));
  handlers.click({ target: { closest: (sel) => (sel === '[data-action]' ? btn : null) } });
  assert.deepEqual(actions, [{ type: 'buy', index: 1 }]);
});

test('mock view: gold is a number, and the shop is closed away from the start tile', () => {
  const state = newGame(9);
  state.player.x = state.map.start.x + 1;
  const view = getView(state);
  assert.equal(typeof view.hud.gold, 'number');
  assert.equal(view.shop.open, false);
  assert.deepEqual(view.shop.stock, []);
});

test('mock view: standing on the shop tile opens it with indexed stock rows', () => {
  const state = newGame(9);
  state.player.x = state.map.start.x;
  state.player.y = state.map.start.y;
  const view = getView(state);
  assert.equal(view.shop.open, true);
  assert.ok(view.shop.stock.length >= 3, 'at least three stock rows');
  view.shop.stock.forEach((row, i) => {
    assert.equal(row.index, i);
    assert.equal(typeof row.kind, 'string');
    assert.equal(row.glyph.length, 1);
    assert.equal(typeof row.price, 'number');
  });
});

test('mock view: the shop tile shows $ in gold once it is in sight', () => {
  const state = newGame(9);
  state.player.x = state.map.start.x + 1;
  const view = getView(state);
  const i = state.map.start.y * view.w + state.map.start.x;
  assert.equal(view.cells[i].ch, '$');
  assert.equal(view.cells[i].fg, '#fbbf24');
});
