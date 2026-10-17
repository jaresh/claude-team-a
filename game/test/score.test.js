import test from 'node:test';
import assert from 'node:assert/strict';
import { score } from '../src/core/score.js';

test('score adds depth, kills, items and win bonus, and takes off traps', () => {
  const stats = { kills: { rat: 1, goblin: 2 }, itemsUsed: 1, trapsTriggered: 2, deepest: 3, damageTaken: 0 };
  assert.equal(score(stats, 'playing'), 300 + 30 + 5 - 4);
  assert.equal(score(stats, 'won'), 300 + 30 + 5 - 4 + 500);
});

test('score counts kills across all kinds', () => {
  const stats = { kills: { rat: 4, bat: 3, slime: 0 }, itemsUsed: 0, trapsTriggered: 0, deepest: 1, damageTaken: 0 };
  assert.equal(score(stats, 'dead'), 100 + 70);
});

test('score is never below 0', () => {
  const stats = { kills: {}, itemsUsed: 0, trapsTriggered: 50, deepest: 1, damageTaken: 0 };
  assert.equal(score(stats, 'dead'), 0);
});
