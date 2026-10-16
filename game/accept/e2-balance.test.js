// Acceptance test for run e2 (lead-owned; teammates do not edit it).
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { playGame } from '../sim/bot.mjs';

const seeds = readFileSync(new URL('../sim/seeds-200.txt', import.meta.url), 'utf8')
  .split('\n').map((s) => s.trim()).filter(Boolean).map(Number);
const games = seeds.map((seed) => playGame(seed, 5000));
const deaths = games.filter((g) => g.status === 'dead');

test('win rate is between 15% and 40%', () => {
  const rate = games.filter((g) => g.status === 'won').length / games.length;
  assert.ok(rate >= 0.15 && rate <= 0.4, `win rate ${rate.toFixed(3)}`);
});

test('mean depth is at least 3.0', () => {
  const mean = games.reduce((sum, g) => sum + g.depth, 0) / games.length;
  assert.ok(mean >= 3.0, `mean depth ${mean.toFixed(2)}`);
});

test('no monster kind causes more than 40% of deaths', () => {
  const counts = {};
  for (const g of deaths) if (g.killedBy) counts[g.killedBy] = (counts[g.killedBy] || 0) + 1;
  const worst = Math.max(0, ...Object.values(counts));
  assert.ok(deaths.length === 0 || worst / deaths.length <= 0.4,
    `deaths by kind ${JSON.stringify(counts)} of ${deaths.length}`);
});
