import { readFileSync } from 'node:fs';
import { playGame } from '/home/jaca/claude-team-a-runs/e4-A/game/sim/bot.mjs';
const seeds = readFileSync('/home/jaca/claude-team-a-runs/e4-A/game/sim/seeds-200.txt', 'utf8')
  .split('\n').map((s) => s.trim()).filter(Boolean).map(Number);
const games = seeds.map((s) => playGame(s, 5000));
const won = games.filter((g) => g.status === 'won').length / games.length;
const depth = games.reduce((a, g) => a + g.depth, 0) / games.length;
const deaths = games.filter((g) => g.status === 'dead');
const counts = {};
for (const g of deaths) counts[g.killedBy ?? 'none'] = (counts[g.killedBy ?? 'none'] || 0) + 1;
console.log(JSON.stringify({ won: won.toFixed(3), depth: depth.toFixed(2), deaths: deaths.length, counts }));
