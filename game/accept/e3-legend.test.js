// Acceptance test for run e3 (lead-owned; teammates do not edit it).
import test from 'node:test';
import assert from 'node:assert/strict';
import { legendRows, poisonLabel } from '../src/ui/legend.js';

test('one legend row per visible monster', () => {
  const view = {
    hud: { poison: 0 },
    visibleMonsters: [
      { kind: 'goblin', glyph: 'g', color: '#5fb3a1', hp: 3, maxHp: 8, ability: 'ranged' },
      { kind: 'rat', glyph: 'r', color: '#b9a37e', hp: 2, maxHp: 3, ability: null },
    ],
  };
  assert.deepEqual(legendRows(view), [
    { text: 'g goblin 3/8 ranged', color: '#5fb3a1' },
    { text: 'r rat 2/3', color: '#b9a37e' },
  ]);
});

test('no legend rows when nothing is in sight', () => {
  assert.deepEqual(legendRows({ hud: { poison: 0 }, visibleMonsters: [] }), []);
});

test('poison label', () => {
  assert.equal(poisonLabel({ hud: { poison: 0 } }), null);
  assert.equal(poisonLabel({ hud: { poison: 2 } }), 'Poisoned (2)');
});
