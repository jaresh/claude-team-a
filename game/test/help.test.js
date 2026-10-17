import { test } from 'node:test';
import assert from 'node:assert/strict';
import { HELP_KEYS, glyphRows } from '../src/ui/help.js';
import { keyToAction, buttonToAction } from '../src/ui/input.js';
import { newGame, getView } from '../src/ui/mock-game.js';

test('HELP_KEYS covers the contract keys', () => {
  const keys = HELP_KEYS.map((r) => r.keys).join(' ');
  for (const k of ['Arrows', 'WASD', 'hjkl', 'yubn', '.', 'g', '>', '1-9', '?', 'Esc']) {
    assert.ok(keys.includes(k), k);
  }
});

test('glyphRows with no traps has you and stairs only', () => {
  assert.deepEqual(glyphRows({ traps: [] }), [
    { glyph: '@', color: '#f8fafc', name: 'you' },
    { glyph: '>', color: '#fde047', name: 'stairs down' },
  ]);
});

test('glyphRows lists each trap kind once, in first-seen order', () => {
  const rows = glyphRows({
    traps: [
      { kind: 'teleport', glyph: '^', color: '#a371f7', x: 1, y: 1 },
      { kind: 'spike', glyph: '^', color: '#c9d1d9', x: 2, y: 1 },
      { kind: 'teleport', glyph: '^', color: '#a371f7', x: 3, y: 1 },
    ],
  });
  assert.deepEqual(rows.slice(2), [
    { glyph: '^', color: '#a371f7', name: 'teleport trap' },
    { glyph: '^', color: '#c9d1d9', name: 'spike trap' },
  ]);
});

test('the mock view carries visible traps for the panel', () => {
  const state = newGame(9);
  const view = getView(state);
  assert.ok(view.traps.length >= 1, 'at least one trap is visible at the start');
  for (const t of view.traps) {
    assert.equal(typeof t.kind, 'string');
    assert.equal(t.glyph.length, 1);
    assert.equal(typeof t.color, 'string');
    assert.equal(typeof t.x, 'number');
    assert.equal(typeof t.y, 'number');
  }
  assert.equal(glyphRows(view).length, 2 + new Set(view.traps.map((t) => t.kind)).size);
});

test('help and close keys and buttons map to actions', () => {
  assert.deepEqual(keyToAction('?'), { type: 'help' });
  assert.deepEqual(keyToAction('Escape'), { type: 'close' });
  assert.deepEqual(buttonToAction({ action: 'help' }), { type: 'help' });
  assert.deepEqual(buttonToAction({ action: 'close' }), { type: 'close' });
});
