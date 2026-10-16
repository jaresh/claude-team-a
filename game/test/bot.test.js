import { test } from 'node:test';
import assert from 'node:assert/strict';
import { newGame, act } from '../src/core/game.js';
import { chooseAction, playGame } from '../sim/bot.mjs';

const SEEDS = [1, 2, 3];

test('chooseAction returns a valid action at turn 0 for 3 seeds', () => {
  const types = new Set(['move', 'wait', 'pickup', 'use', 'descend']);
  for (const seed of SEEDS) {
    const state = newGame(seed);
    const action = chooseAction(state);
    assert.ok(types.has(action.type), `seed ${seed}: unknown action ${action.type}`);
    if (action.type === 'move') {
      assert.ok(Number.isInteger(action.dx) && action.dx >= -1 && action.dx <= 1);
      assert.ok(Number.isInteger(action.dy) && action.dy >= -1 && action.dy <= 1);
      assert.ok(action.dx !== 0 || action.dy !== 0);
    }
    if (action.type === 'use') {
      assert.ok(action.index >= 0 && action.index < state.player.inventory.length);
    }
    // The action must be accepted by the game and advance the turn (or be a no-op on wait-free paths).
    const before = state.turn;
    act(state, action);
    assert.ok(state.turn >= before);
  }
});

test('playGame ends (dead, won or maxTurns) for 3 seeds with maxTurns 2000', () => {
  for (const seed of SEEDS) {
    const r = playGame(seed, 2000);
    assert.ok(['dead', 'won', 'maxTurns'].includes(r.status), `seed ${seed}: ${r.status}`);
    assert.ok(r.turns <= 2000);
    assert.ok(r.depth >= 1 && r.depth <= 5);
    if (r.status !== 'dead') assert.equal(r.killedBy, null);
  }
});

test('playGame gives the same result twice for the same seed', () => {
  for (const seed of SEEDS) {
    assert.deepEqual(playGame(seed, 2000), playGame(seed, 2000));
  }
});
