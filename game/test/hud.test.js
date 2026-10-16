import { test } from 'node:test';
import assert from 'node:assert/strict';
import { endMessage, hpColor } from '../src/ui/hud.js';

const view = (status, depth, turn) => ({ status, hud: { depth, turn } });

test('endMessage is null while playing', () => {
  assert.equal(endMessage(view('playing', 2, 50)), null);
});

test('endMessage names the depth and turn on death', () => {
  assert.equal(endMessage(view('dead', 3, 120)), 'You died on depth 3 after 120 turns.');
});

test('endMessage celebrates a win', () => {
  assert.equal(endMessage(view('won', 5, 900)), 'You won! Depth 5 in 900 turns.');
});

test('hpColor is green above half health', () => {
  assert.equal(hpColor(20, 20), '#3fb950');
  assert.equal(hpColor(11, 20), '#3fb950');
});

test('hpColor is amber from a quarter to half health', () => {
  assert.equal(hpColor(10, 20), '#d29922');
  assert.equal(hpColor(6, 20), '#d29922');
});

test('hpColor is red at a quarter health or below', () => {
  assert.equal(hpColor(5, 20), '#f85149');
  assert.equal(hpColor(0, 20), '#f85149');
});
