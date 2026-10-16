import { test } from 'node:test';
import assert from 'node:assert/strict';
import { legendRows, poisonLabel } from '../src/ui/legend.js';
import { newGame, getView } from '../src/ui/mock-game.js';

const monster = (over = {}) => ({
  kind: 'rat', glyph: 'r', color: '#b9a37e', hp: 2, maxHp: 3, ability: null, ...over,
});

test('legend row has glyph, kind and hp, with no ability suffix when ability is null', () => {
  assert.deepEqual(legendRows({ visibleMonsters: [monster()] }), [
    { text: 'r rat 2/3', color: '#b9a37e' },
  ]);
});

test('legend row appends the ability name when there is one', () => {
  const view = { visibleMonsters: [monster({ kind: 'bat', glyph: 'b', ability: 'regen' })] };
  assert.deepEqual(legendRows(view), [{ text: 'b bat 2/3 regen', color: '#b9a37e' }]);
});

test('legend rows keep the order of visibleMonsters', () => {
  const view = { visibleMonsters: [monster({ kind: 'orc' }), monster({ kind: 'imp' })] };
  assert.deepEqual(legendRows(view).map((r) => r.text), ['r orc 2/3', 'r imp 2/3']);
});

test('poison label is null for zero or missing poison', () => {
  assert.equal(poisonLabel({ hud: { poison: 0 } }), null);
  assert.equal(poisonLabel({ hud: {} }), null);
});

test('poison label shows the turns left', () => {
  assert.equal(poisonLabel({ hud: { poison: 3 } }), 'Poisoned (3)');
});

test('mock getView lists the visible monsters and a zero poison count', () => {
  const view = getView(newGame(9));
  assert.equal(view.hud.poison, 0);
  assert.ok(Array.isArray(view.visibleMonsters));
  for (const m of view.visibleMonsters) {
    for (const field of ['kind', 'glyph', 'color', 'hp', 'maxHp', 'ability']) {
      assert.ok(field in m, `visibleMonsters entry has ${field}`);
    }
  }
});

test('mock getView leaves out monsters outside sight', () => {
  const state = newGame(9);
  state.monsters[0].x = 1;
  state.monsters[0].y = 12;
  state.player.x = 22;
  state.player.y = 1;
  state.visible = new Set();
  assert.deepEqual(getView(state).visibleMonsters, []);
});
