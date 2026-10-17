import { test } from 'node:test';
import assert from 'node:assert/strict';
import { HELP_KEYS, glyphRows } from '../src/ui/help.js';
import { getView, newGame } from '../src/ui/mock-game.js';

test('HELP_KEYS rows have a keys string and an action string', () => {
  for (const r of HELP_KEYS) {
    assert.equal(typeof r.keys, 'string');
    assert.ok(r.keys.length > 0);
    assert.equal(typeof r.action, 'string');
  }
});

test('glyphRows with no traps is you then stairs', () => {
  assert.deepEqual(glyphRows({ traps: [] }), [
    { glyph: '@', color: '#f8fafc', name: 'you' },
    { glyph: '>', color: '#fde047', name: 'stairs down' },
  ]);
});

test('glyphRows gives one row per trap kind, first-seen order, using that trap colour', () => {
  const rows = glyphRows({
    traps: [
      { kind: 'poison', glyph: '^', color: '#3fb950', x: 1, y: 1 },
      { kind: 'spike', glyph: '^', color: '#c9d1d9', x: 2, y: 1 },
      { kind: 'poison', glyph: '^', color: '#3fb950', x: 5, y: 5 },
    ],
  });
  assert.deepEqual(rows.slice(2), [
    { glyph: '^', color: '#3fb950', name: 'poison trap' },
    { glyph: '^', color: '#c9d1d9', name: 'spike trap' },
  ]);
});

test('the mock view carries visible traps for the panel', () => {
  const state = newGame(9);
  const view = getView(state);
  assert.ok(Array.isArray(view.traps));
  for (const t of view.traps) {
    assert.equal(typeof t.kind, 'string');
    assert.equal(typeof t.glyph, 'string');
    assert.equal(typeof t.color, 'string');
  }
  const names = glyphRows({ traps: state.traps.map((t) => ({ ...t })) }).map((r) => r.name);
  assert.ok(names.includes('spike trap'));
  assert.ok(names.includes('teleport trap'));
});
