// Greedy bot for the game. Plays seeds headless and writes per-seed stats plus a summary.
// Usage: node game/sim/bot.mjs --seeds <file> --out <file>
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { newGame, act } from '../src/core/game.js';
import { isWalkable, STAIRS } from '../src/core/map.js';

const MAX_TURNS = 5000;
const DIRS = [[-1, -1], [0, -1], [1, -1], [-1, 0], [1, 0], [-1, 1], [0, 1], [1, 1]];
const HIT_LINE = /^The (.+) hits you for \d+\.$/;

function cheb(ax, ay, bx, by) {
  return Math.max(Math.abs(ax - bx), Math.abs(ay - by));
}

// First step of the shortest path over explored walkable tiles to the nearest tile where isGoal
// holds (the start tile is never a goal). Returns {dx, dy} or null when no goal is reachable.
function firstStepTo(state, isGoal) {
  const { map, explored, player } = state;
  const w = map.w;
  const start = player.y * w + player.x;
  const prev = new Int32Array(w * map.h).fill(-1);
  const seen = new Uint8Array(w * map.h);
  const queue = [start];
  seen[start] = 1;
  let goal = -1;
  for (let head = 0; head < queue.length; head++) {
    const cur = queue[head];
    if (cur !== start && isGoal(cur)) {
      goal = cur;
      break;
    }
    const cx = cur % w, cy = Math.floor(cur / w);
    for (const [dx, dy] of DIRS) {
      const nx = cx + dx, ny = cy + dy;
      if (!isWalkable(map, nx, ny)) continue;
      const ni = ny * w + nx;
      if (seen[ni] || !explored[ni]) continue;
      seen[ni] = 1;
      prev[ni] = cur;
      queue.push(ni);
    }
  }
  if (goal < 0) return null;
  let node = goal;
  while (prev[node] !== start) node = prev[node];
  return { dx: (node % w) - player.x, dy: Math.floor(node / w) - player.y };
}

// An explored walkable tile with at least one in-bounds neighbour that is not explored yet.
function isFrontier(state, i) {
  const { map, explored } = state;
  const x = i % map.w, y = Math.floor(i / map.w);
  for (const [dx, dy] of DIRS) {
    const nx = x + dx, ny = y + dy;
    if (nx < 0 || ny < 0 || nx >= map.w || ny >= map.h) continue;
    if (!explored[ny * map.w + nx]) return true;
  }
  return false;
}

// Picks one action. Order: attack adjacent monster; heal if hp < 40%; pick up item underfoot;
// stairs (descend if on them, walk if explored); walk to nearest frontier; otherwise wait.
export function chooseAction(state) {
  if (state.status !== 'playing') return { type: 'wait' };
  const p = state.player;
  const map = state.map;
  const pIdx = p.y * map.w + p.x;

  const adjacent = state.monsters.filter((m) => m.hp > 0 && cheb(m.x, m.y, p.x, p.y) === 1);
  if (adjacent.length > 0) {
    const target = adjacent.reduce((a, b) => (b.hp < a.hp ? b : a));
    return { type: 'move', dx: target.x - p.x, dy: target.y - p.y };
  }

  if (p.hp < 0.4 * p.maxHp) {
    const index = p.inventory.findIndex((it) => it.effect === 'heal');
    if (index >= 0) return { type: 'use', index };
  }

  if (state.items.some((it) => it.x === p.x && it.y === p.y)) return { type: 'pickup' };

  if (map.tiles[pIdx] === STAIRS) return { type: 'descend' };
  const stIdx = map.stairs.y * map.w + map.stairs.x;
  if (state.explored[stIdx]) {
    const step = firstStepTo(state, (i) => i === stIdx);
    if (step) return { type: 'move', ...step };
  }

  const step = firstStepTo(state, (i) => isFrontier(state, i));
  if (step) return { type: 'move', ...step };

  return { type: 'wait' };
}

// Kind of the monster in the last "hits you" line. The killing blow is always the last one.
function lastHitter(log) {
  for (let i = log.length - 1; i >= 0; i--) {
    const m = HIT_LINE.exec(log[i]);
    if (m) return m[1];
  }
  return null;
}

export function playGame(seed, maxTurns = MAX_TURNS) {
  const state = newGame(seed);
  // Guard against a loop of actions that take no turn.
  let guard = 0;
  while (state.status === 'playing' && state.turn < maxTurns && guard++ < maxTurns * 4) {
    act(state, chooseAction(state));
  }
  const status = state.status === 'playing' ? 'maxTurns' : state.status;
  return {
    seed,
    status,
    depth: state.depth,
    turns: state.turn,
    level: state.player.level,
    killedBy: status === 'dead' ? lastHitter(state.log) : null,
  };
}

function summarize(seeds) {
  const games = seeds.length;
  const won = seeds.filter((r) => r.status === 'won').length;
  const mean = (key) => (games === 0 ? 0 : seeds.reduce((s, r) => s + r[key], 0) / games);
  const deathsByKind = {};
  for (const r of seeds) {
    if (r.killedBy !== null) deathsByKind[r.killedBy] = (deathsByKind[r.killedBy] || 0) + 1;
  }
  return {
    games,
    winRate: games === 0 ? 0 : won / games,
    meanDepth: mean('depth'),
    meanTurns: mean('turns'),
    deathsByKind,
  };
}

function parseArgs(argv) {
  const out = {};
  for (let i = 0; i < argv.length; i += 2) {
    const key = argv[i];
    if (key === '--seeds' || key === '--out') out[key.slice(2)] = argv[i + 1];
  }
  return out;
}

function readSeeds(path) {
  return readFileSync(path, 'utf8')
    .split('\n')
    .map((s) => s.trim())
    .filter((s) => s.length > 0 && !s.startsWith('#'))
    .map((s) => (/^-?\d+$/.test(s) ? Number(s) : s));
}

const isMain = process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href;
if (isMain) {
  const args = parseArgs(process.argv.slice(2));
  if (!args.seeds || !args.out) {
    console.error('usage: node game/sim/bot.mjs --seeds <file> --out <file>');
    process.exit(1);
  }
  const seeds = readSeeds(args.seeds).map((seed) => playGame(seed, MAX_TURNS));
  const result = { seeds, summary: summarize(seeds) };
  mkdirSync(dirname(resolve(args.out)), { recursive: true });
  writeFileSync(resolve(args.out), JSON.stringify(result, null, 2) + '\n');
  console.log(JSON.stringify(result.summary));
}
