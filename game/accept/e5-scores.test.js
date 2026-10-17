// Acceptance test for run e5 (lead-owned; teammates do not edit it).
import test from 'node:test';
import assert from 'node:assert/strict';
import { MAX_SCORES, SCORES_KEY, addScore, loadScores, saveScores, summaryRows } from '../src/ui/scores.js';

function fakeStorage(init = {}) {
  const data = { ...init };
  return { data, getItem: (k) => (k in data ? data[k] : null), setItem: (k, v) => { data[k] = String(v); } };
}
const entry = (score, turns) => ({ score, depth: 2, turns, seed: 1, won: false });

test('addScore sorts, breaks ties by turns, keeps the top 5, and leaves the list alone', () => {
  const list = [entry(300, 50), entry(100, 10)];
  const out = addScore(list, entry(300, 40));
  assert.deepEqual(out.map((e) => [e.score, e.turns]), [[300, 40], [300, 50], [100, 10]]);
  assert.equal(list.length, 2);
  let many = [];
  for (let i = 0; i < 8; i++) many = addScore(many, entry(i * 10, 5));
  assert.equal(MAX_SCORES, 5);
  assert.deepEqual(many.map((e) => e.score), [70, 60, 50, 40, 30]);
});

test('scores load and save as JSON under one key', () => {
  assert.equal(SCORES_KEY, 'roguelike-scores');
  const s = fakeStorage();
  assert.deepEqual(loadScores(s), []);
  saveScores(s, [entry(10, 3)]);
  assert.deepEqual(JSON.parse(s.data[SCORES_KEY]), [entry(10, 3)]);
  assert.deepEqual(loadScores(s), [entry(10, 3)]);
  assert.deepEqual(loadScores(fakeStorage({ [SCORES_KEY]: 'not json' })), []);
  assert.deepEqual(loadScores(fakeStorage({ [SCORES_KEY]: '{"a":1}' })), []);
});

test('summary rows', () => {
  const view = {
    score: 434, hud: { turn: 210 },
    stats: { kills: { rat: 2, goblin: 1 }, itemsUsed: 2, trapsTriggered: 3, deepest: 4, damageTaken: 30 },
  };
  assert.deepEqual(summaryRows(view), [
    { label: 'Score', value: 434 },
    { label: 'Depth reached', value: 4 },
    { label: 'Turns', value: 210 },
    { label: 'Kills', value: 3 },
    { label: 'Items used', value: 2 },
    { label: 'Traps triggered', value: 3 },
    { label: 'Damage taken', value: 30 },
  ]);
});
