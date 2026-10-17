import test from 'node:test';
import assert from 'node:assert/strict';
import { HELP_KEYS, glyphRows } from '../src/ui/help.js';
import { keyToAction, buttonToAction } from '../src/ui/input.js';

test('HELP_KEYS has a non-empty keys and action on every row', () => {
  for (const r of HELP_KEYS) {
    assert.ok(r.keys.length > 0);
    assert.ok(r.action.length > 0);
  }
});

test('glyphRows with no traps is just you and the stairs', () => {
  assert.deepEqual(glyphRows({ traps: [] }), [
    { glyph: '@', color: '#f8fafc', name: 'you' },
    { glyph: '>', color: '#fde047', name: 'stairs down' },
  ]);
});

test('glyphRows keeps one row per trap kind, using the first trap seen', () => {
  const rows = glyphRows({
    traps: [
      { kind: 'spike', glyph: '^', color: '#c9d1d9', x: 1, y: 1 },
      { kind: 'spike', glyph: '^', color: '#ff0000', x: 2, y: 2 },
    ],
  });
  assert.equal(rows.length, 3);
  assert.deepEqual(rows[2], { glyph: '^', color: '#c9d1d9', name: 'spike trap' });
});

test('help and close keys and buttons map to UI-only actions', () => {
  assert.deepEqual(keyToAction('?'), { type: 'help' });
  assert.deepEqual(keyToAction('Escape'), { type: 'close' });
  assert.deepEqual(buttonToAction({ action: 'help' }), { type: 'help' });
  assert.deepEqual(buttonToAction({ action: 'close' }), { type: 'close' });
});
