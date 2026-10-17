import test from 'node:test';
import assert from 'node:assert/strict';
import { score } from '../src/core/score.js';

const EMPTY = { kills: {}, itemsUsed: 0, trapsTriggered: 0, deepest: 1, damageTaken: 0 };

test('score adds depth, kills of every kind, items used; traps count against it', () => {
  const stats = { ...EMPTY, kills: { rat: 1, bat: 2 }, itemsUsed: 3, trapsTriggered: 1, deepest: 2 };
  assert.equal(score(stats, 'playing'), 200 + 30 + 15 - 2);
});

test('damage taken does not change the score', () => {
  assert.equal(score({ ...EMPTY, damageTaken: 50 }, 'dead'), score(EMPTY, 'dead'));
});

test('a won game adds 500', () => {
  assert.equal(score(EMPTY, 'won') - score(EMPTY, 'dead'), 500);
});

test('the score is never below 0', () => {
  assert.equal(score({ ...EMPTY, trapsTriggered: 100 }, 'dead'), 0);
});
