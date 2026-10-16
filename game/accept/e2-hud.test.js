// Acceptance test for run e2 (lead-owned; teammates do not edit it).
import test from 'node:test';
import assert from 'node:assert/strict';
import { endMessage, hpColor } from '../src/ui/hud.js';

const view = (status, depth, turn) => ({ status, hud: { depth, turn } });

test('no end message while playing', () => {
  assert.equal(endMessage(view('playing', 2, 50)), null);
});

test('end message on death', () => {
  assert.equal(endMessage(view('dead', 3, 120)), 'You died on depth 3 after 120 turns.');
});

test('end message on a win', () => {
  assert.equal(endMessage(view('won', 5, 900)), 'You won! Depth 5 in 900 turns.');
});

test('hp colour thresholds', () => {
  assert.equal(hpColor(11, 20), '#3fb950');
  assert.equal(hpColor(10, 20), '#d29922');
  assert.equal(hpColor(6, 20), '#d29922');
  assert.equal(hpColor(5, 20), '#f85149');
});
