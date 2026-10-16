import { test } from 'node:test';
import assert from 'node:assert/strict';
import { legendRows, poisonLabel } from '../src/ui/legend.js';

test('legendRows: one row per visible monster, in its colour', () => {
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

test('legendRows: no rows when nothing is in sight', () => {
  assert.deepEqual(legendRows({ hud: { poison: 0 }, visibleMonsters: [] }), []);
});

test('legendRows: each ability name is shown after the hp', () => {
  const view = {
    visibleMonsters: ['regen', 'poison'].map((ability) => ({
      kind: 'troll', glyph: 'T', color: '#22c55e', hp: 9, maxHp: 9, ability,
    })),
  };
  assert.deepEqual(legendRows(view).map((r) => r.text), ['T troll 9/9 regen', 'T troll 9/9 poison']);
});

test('poisonLabel: null when not poisoned, turns left otherwise', () => {
  assert.equal(poisonLabel({ hud: { poison: 0 } }), null);
  assert.equal(poisonLabel({ hud: { poison: 2 } }), 'Poisoned (2)');
});
