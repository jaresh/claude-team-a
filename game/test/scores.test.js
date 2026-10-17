import { test } from 'node:test';
import assert from 'node:assert/strict';
import { MAX_SCORES, SCORES_KEY, addScore, loadScores, saveScores, summaryRows } from '../src/ui/scores.js';
import { newGame, act, getView } from '../src/ui/mock-game.js';
import { score } from '../src/core/score.js';

const entry = (s, turns) => ({ score: s, depth: 1, turns, seed: 1, won: false });

test('addScore: returns a new list and leaves the input alone', () => {
  const list = [entry(50, 9)];
  const out = addScore(list, entry(70, 3));
  assert.notEqual(out, list);
  assert.deepEqual(list, [entry(50, 9)]);
  assert.deepEqual(out.map((e) => e.score), [70, 50]);
});

test('addScore: equal score and equal turns keep the older entry first', () => {
  const first = { ...entry(10, 5), seed: 'a' };
  const second = { ...entry(10, 5), seed: 'b' };
  const out = addScore([first], second);
  assert.deepEqual(out.map((e) => e.seed), ['a', 'b']);
});

test('addScore: the list never grows past MAX_SCORES', () => {
  let list = [];
  for (let i = 0; i < 20; i++) list = addScore(list, entry(i, 1));
  assert.equal(list.length, MAX_SCORES);
});

test('loadScores: reads back what saveScores wrote', () => {
  const data = {};
  const storage = { getItem: (k) => (k in data ? data[k] : null), setItem: (k, v) => { data[k] = v; } };
  const list = [entry(30, 4), entry(20, 2)];
  saveScores(storage, list);
  assert.deepEqual(loadScores(storage), list);
});

test('loadScores: a storage that throws gives an empty list', () => {
  const storage = { getItem: () => { throw new Error('blocked'); }, setItem() {} };
  assert.deepEqual(loadScores(storage), []);
});

test('summaryRows: no kills gives Kills 0', () => {
  const view = {
    score: 0, hud: { turn: 0 },
    stats: { kills: {}, itemsUsed: 0, trapsTriggered: 0, deepest: 1, damageTaken: 0 },
  };
  assert.equal(summaryRows(view)[3].value, 0);
});

test('mock game: a fresh game has the stats shape and score matches the core formula', () => {
  const view = getView(newGame(7));
  assert.deepEqual(view.stats, { kills: {}, itemsUsed: 0, trapsTriggered: 0, deepest: 1, damageTaken: 0 });
  assert.equal(view.score, score(view.stats, view.status));
});

test('mock game: getView copies stats, kills included', () => {
  const state = newGame(7);
  const view = getView(state);
  view.stats.kills.rat = 99;
  view.stats.itemsUsed = 99;
  assert.deepEqual(state.stats.kills, {});
  assert.equal(state.stats.itemsUsed, 0);
});

test('mock game: killing a monster counts it under its kind', () => {
  const state = newGame(7);
  const p = state.player;
  state.monsters = [{ id: 9, kind: 'rat', glyph: 'r', color: '#fff', x: p.x + 1, y: p.y, hp: 1, maxHp: 1, atk: 1, def: 0, xp: 1, ability: null }];
  act(state, { type: 'move', dx: 1, dy: 0 });
  assert.equal(state.stats.kills.rat, 1);
});

test('mock game: using an item counts as an item used', () => {
  const state = newGame(7);
  state.player.inventory.push({ id: 4, kind: 'potion', glyph: '!', color: '#f0f', effect: 'heal', amount: 2 });
  act(state, { type: 'use', index: 0 });
  assert.equal(state.stats.itemsUsed, 1);
});

test('mock game: a monster hit adds to damageTaken', () => {
  const state = newGame(7);
  const p = state.player;
  state.monsters = [{ id: 9, kind: 'rat', glyph: 'r', color: '#fff', x: p.x + 1, y: p.y, hp: 9, maxHp: 9, atk: 4, def: 0, xp: 1, ability: null }];
  act(state, { type: 'wait' });
  assert.equal(state.stats.damageTaken, 4 - p.def);
});

test('mock game: descending raises deepest', () => {
  const state = newGame(7);
  state.player.x = state.map.stairs.x;
  state.player.y = state.map.stairs.y;
  act(state, { type: 'descend' });
  assert.equal(state.stats.deepest, 2);
  assert.equal(getView(state).stats.deepest, 2);
});

test('SCORES_KEY is the key the storage uses', () => {
  const data = {};
  saveScores({ setItem: (k, v) => { data[k] = v; } }, [entry(1, 1)]);
  assert.deepEqual(Object.keys(data), [SCORES_KEY]);
});
