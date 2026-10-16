import test from 'node:test';
import assert from 'node:assert/strict';
import { newGame, act, getView } from '../src/core/game.js';

// A visible tile at Chebyshev distance `d` from the player, or null.
function visibleAt(state, d) {
  const { map, player } = state;
  for (const i of state.visible) {
    const x = i % map.w, y = Math.floor(i / map.w);
    if (Math.max(Math.abs(x - player.x), Math.abs(y - player.y)) === d) return { x, y };
  }
  return null;
}

const monster = (fields) => ({ id: 900, kind: 'test', glyph: 't', color: '#ffffff', hp: 5, maxHp: 5,
  atk: 2, def: 0, xp: 0, ability: null, ...fields });

test('a ranged shot does atk - 1 (at least 1) and logs the damage', () => {
  const state = newGame(4);
  const spot = visibleAt(state, 3);
  assert.ok(spot, 'no visible tile 3 away');
  state.monsters = [monster({ ...spot, atk: 3, ability: 'ranged' })];
  state.player.def = 0;
  const hp = state.player.hp;
  act(state, { type: 'wait' });
  const dealt = hp - state.player.hp;
  assert.ok(dealt >= 2 && dealt <= 4, `shot did ${dealt}, expected 2 to 4`);
  assert.ok(state.log.includes(`The test shoots you for ${dealt}.`), state.log.join(' | '));
});

test('a melee hit from a poison monster poisons the player for 3 turns', () => {
  const state = newGame(4);
  const spot = visibleAt(state, 1);
  assert.ok(spot, 'no visible tile next to the player');
  state.monsters = [monster({ ...spot, ability: 'poison' })];
  act(state, { type: 'wait' });
  assert.equal(state.player.poison, 2, 'poison left after one tick');
  assert.equal(getView(state).hud.poison, 2);
});

test('a plain melee hit does not poison', () => {
  const state = newGame(4);
  const spot = visibleAt(state, 1);
  state.monsters = [monster({ ...spot, ability: null })];
  act(state, { type: 'wait' });
  assert.equal(state.player.poison, 0);
  assert.equal(getView(state).hud.poison, 0);
});

test('dying from poison is an ordinary death', () => {
  const state = newGame(1);
  state.monsters = [];
  state.player.hp = 1;
  state.player.poison = 2;
  act(state, { type: 'wait' });
  assert.equal(state.player.hp, 0);
  assert.equal(state.status, 'dead');
  assert.equal(state.log.at(-1), 'You die.');
  assert.ok(state.log.includes('Poison hurts you.'));
});
