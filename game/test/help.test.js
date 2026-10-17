import { test } from 'node:test';
import assert from 'node:assert/strict';
import { HELP_KEYS, glyphRows } from '../src/ui/help.js';
import { keyToAction, buttonToAction } from '../src/ui/input.js';
import { newGame, getView } from '../src/ui/mock-game.js';

test('HELP_KEYS: every row has keys and an action, and covers the main controls', () => {
  for (const r of HELP_KEYS) {
    assert.equal(typeof r.keys, 'string');
    assert.equal(typeof r.action, 'string');
  }
  const keys = HELP_KEYS.map((r) => r.keys).join(' ');
  for (const k of ['Arrows', 'WASD', 'hjkl', 'yubn', '.', 'g', '>', '1-9', '?', 'Esc']) {
    assert.ok(keys.includes(k), k);
  }
});

test('glyphRows: you and stairs with no traps in view', () => {
  assert.deepEqual(glyphRows({ traps: [] }), [
    { glyph: '@', color: '#f8fafc', name: 'you' },
    { glyph: '>', color: '#fde047', name: 'stairs down' },
  ]);
});

test('glyphRows: one row per trap kind, first-seen order, using that trap glyph and colour', () => {
  const view = {
    traps: [
      { kind: 'spike', glyph: '^', color: '#c9d1d9', x: 1, y: 1 },
      { kind: 'teleport', glyph: '*', color: '#a371f7', x: 2, y: 1 },
      { kind: 'spike', glyph: '^', color: '#c9d1d9', x: 3, y: 1 },
    ],
  };
  const rows = glyphRows(view);
  assert.deepEqual(rows.slice(2), [
    { glyph: '^', color: '#c9d1d9', name: 'spike trap' },
    { glyph: '*', color: '#a371f7', name: 'teleport trap' },
  ]);
});

test('glyphRows: a view without a traps field still gives the two base rows', () => {
  assert.equal(glyphRows({}).length, 2);
});

test('keyToAction: ? opens help, Escape closes it', () => {
  assert.deepEqual(keyToAction('?'), { type: 'help' });
  assert.deepEqual(keyToAction('Escape'), { type: 'close' });
});

test('buttonToAction: the help button', () => {
  assert.deepEqual(buttonToAction({ action: 'help' }), { type: 'help' });
});

test('mock view: traps are listed only when in sight', () => {
  const state = newGame(11);
  const view = getView(state);
  assert.ok(Array.isArray(view.traps));
  assert.ok(view.traps.length >= 1, 'mock has a trap in sight at the start');
  for (const t of view.traps) {
    assert.equal(typeof t.kind, 'string');
    assert.equal(t.glyph.length, 1);
    assert.equal(typeof t.color, 'string');
  }
});
