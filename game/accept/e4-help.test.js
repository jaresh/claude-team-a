// Acceptance test for run e4 (lead-owned; teammates do not edit it).
import test from 'node:test';
import assert from 'node:assert/strict';
import { HELP_KEYS, glyphRows } from '../src/ui/help.js';
import { keyToAction, buttonToAction } from '../src/ui/input.js';

test('help lists the keys', () => {
  assert.ok(HELP_KEYS.length >= 7);
  for (const r of HELP_KEYS) {
    assert.equal(typeof r.keys, 'string');
    assert.equal(typeof r.action, 'string');
  }
  const keys = HELP_KEYS.map((r) => r.keys).join(' ');
  for (const k of ['?', '>', 'g', '.', 'Esc', '1']) assert.ok(keys.includes(k), k);
});

test('glyph rows: you, stairs, then one per trap kind', () => {
  const view = {
    traps: [
      { kind: 'spike', glyph: '^', color: '#c9d1d9', x: 1, y: 1 },
      { kind: 'teleport', glyph: '^', color: '#a371f7', x: 2, y: 1 },
      { kind: 'spike', glyph: '^', color: '#c9d1d9', x: 3, y: 1 },
    ],
  };
  assert.deepEqual(glyphRows(view), [
    { glyph: '@', color: '#f8fafc', name: 'you' },
    { glyph: '>', color: '#fde047', name: 'stairs down' },
    { glyph: '^', color: '#c9d1d9', name: 'spike trap' },
    { glyph: '^', color: '#a371f7', name: 'teleport trap' },
  ]);
  assert.equal(glyphRows({ traps: [] }).length, 2);
});

test('help and close actions', () => {
  assert.deepEqual(keyToAction('?'), { type: 'help' });
  assert.deepEqual(keyToAction('Escape'), { type: 'close' });
  assert.deepEqual(buttonToAction({ action: 'help' }), { type: 'help' });
});
