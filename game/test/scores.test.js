import { test } from 'node:test';
import assert from 'node:assert/strict';
import { addScore, loadScores, summaryRows, MAX_SCORES } from '../src/ui/scores.js';
import { newGame, act, getView } from '../src/ui/mock-game.js';

test('addScore leaves its input list unchanged and keeps the list at MAX_SCORES', () => {
  const list = [];
  let out = list;
  for (let i = 0; i < MAX_SCORES + 3; i++) out = addScore(out, { score: i, depth: 1, turns: 1, seed: 1, won: false });
  assert.equal(list.length, 0);
  assert.equal(out.length, MAX_SCORES);
  assert.equal(out[0].score, MAX_SCORES + 2);
});

test('loadScores returns the stored list when it is a JSON array', () => {
  const storage = { getItem: () => '[{"score":5,"depth":1,"turns":2,"seed":3,"won":false}]', setItem() {} };
  assert.deepEqual(loadScores(storage), [{ score: 5, depth: 1, turns: 2, seed: 3, won: false }]);
});

test('mock view carries stats and a score, and stats is a copy', () => {
  const state = newGame(9);
  const view = getView(state);
  for (const k of ['kills', 'itemsUsed', 'trapsTriggered', 'deepest', 'damageTaken']) {
    assert.ok(k in view.stats, k);
  }
  assert.equal(typeof view.score, 'number');
  view.stats.kills.rat = 99;
  assert.deepEqual(state.stats.kills, {});
});

test('mock descend raises deepest, and the score counts it', () => {
  const state = newGame(9);
  const before = getView(state).score;
  state.map.tiles.fill('>');
  act(state, { type: 'descend' });
  const view = getView(state);
  assert.equal(view.stats.deepest, 2);
  assert.ok(view.score > before);
});

test('summaryRows gives seven labelled numbers from a mock view', () => {
  const rows = summaryRows(getView(newGame(4)));
  assert.equal(rows.length, 7);
  for (const r of rows) assert.equal(typeof r.value, 'number', r.label);
});
