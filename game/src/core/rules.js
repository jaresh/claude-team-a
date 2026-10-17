// Game rules: spawning, combat, items and monster movement. Pure: no DOM, no Math.random.
// The map.js constants are repeated here because this module must not import core/map.js.
import { MONSTERS } from '../data/monsters.js';
import { ITEMS } from '../data/items.js';
import { TRAPS } from '../data/traps.js';

const FLOOR = '.', STAIRS = '>';
const NEIGHBOURS = [[-1, -1], [0, -1], [1, -1], [-1, 0], [1, 0], [-1, 1], [0, 1], [1, 1]];

function tileIndex(map, x, y) {
  return y * map.w + x;
}

function walkable(map, x, y) {
  if (x < 0 || y < 0 || x >= map.w || y >= map.h) return false;
  const c = map.tiles[y * map.w + x];
  return c === FLOOR || c === STAIRS;
}

function chebyshev(ax, ay, bx, by) {
  return Math.max(Math.abs(ax - bx), Math.abs(ay - by));
}

// Free FLOOR tile indices: not occupied, not the start and not the stairs.
function freeFloorTiles(map, occupied) {
  const start = tileIndex(map, map.start.x, map.start.y);
  const stairs = tileIndex(map, map.stairs.x, map.stairs.y);
  const out = [];
  for (let i = 0; i < map.tiles.length; i++) {
    if (map.tiles[i] === FLOOR && i !== start && i !== stairs && !occupied.has(i)) out.push(i);
  }
  return out;
}

// Spawns up to `count` entities from `table` rows with minDepth <= depth.
// Stops early if no free tile is left. Each tile is used at most once and is added to `occupied`.
function spawnFrom(rng, map, depth, occupied, count, table, make) {
  const eligible = table.filter((row) => row.minDepth <= depth);
  const free = freeFloorTiles(map, occupied);
  const out = [];
  if (eligible.length === 0) return out;
  for (let n = 0; n < count && free.length > 0; n++) {
    const row = rng.pick(eligible);
    const k = rng.int(0, free.length - 1);
    const [i] = free.splice(k, 1);
    occupied.add(i);
    // Tile index + 1 is unique per level, since no two spawns share a tile.
    out.push(make(row, i + 1, i % map.w, Math.floor(i / map.w)));
  }
  return out;
}

export function spawnMonsters(rng, map, depth, occupied) {
  return spawnFrom(rng, map, depth, occupied, 2 + Math.floor(depth / 2), MONSTERS, (row, id, x, y) => ({
    id,
    kind: row.kind,
    glyph: row.glyph,
    color: row.color,
    x,
    y,
    hp: row.hp,
    maxHp: row.hp,
    atk: row.atk,
    def: row.def,
    xp: row.xp,
    ability: row.ability,
  }));
}

export function spawnItems(rng, map, depth, occupied) {
  return spawnFrom(rng, map, depth, occupied, 4 + Math.floor(depth / 2), ITEMS, (row, id, x, y) => ({
    id,
    kind: row.kind,
    glyph: row.glyph,
    color: row.color,
    effect: row.effect,
    amount: row.amount,
    x,
    y,
  }));
}

// Traps start hidden. Their ids are unique per level, as the spawn tiles are not shared.
export function spawnTraps(rng, map, depth, occupied) {
  return spawnFrom(rng, map, depth, occupied, 1 + depth, TRAPS, (row, id, x, y) => ({
    id,
    kind: row.kind,
    glyph: row.glyph,
    color: row.color,
    effect: row.effect,
    amount: row.amount,
    x,
    y,
    hidden: true,
  }));
}

export function attack(attacker, defender, rng) {
  const damage = Math.max(1, attacker.atk + rng.int(0, 2) - defender.def);
  defender.hp -= damage;
  return { damage, killed: defender.hp <= 0 };
}

export function applyItem(player, item) {
  switch (item.effect) {
    case 'heal': {
      const before = player.hp;
      player.hp = Math.min(player.maxHp, player.hp + item.amount);
      return `You drink the ${item.kind} and recover ${player.hp - before} hp.`;
    }
    case 'atk':
      player.atk += item.amount;
      return `The ${item.kind} sharpens your blade: +${item.amount} attack.`;
    case 'def':
      player.def += item.amount;
      return `The ${item.kind} hardens your guard: +${item.amount} defence.`;
    default:
      return `The ${item.kind} does nothing.`;
  }
}

export function monsterStep(map, monster, player, visible, isBlocked, rng) {
  if (visible.has(tileIndex(map, monster.x, monster.y))) {
    const dist = chebyshev(monster.x, monster.y, player.x, player.y);
    if (dist === 1) return { type: 'attack' };
    if (monster.ability === 'ranged' && dist >= 2 && dist <= 4) return { type: 'shoot' };
    let best = null, bestCheb = Infinity, bestSq = Infinity;
    for (const [dx, dy] of NEIGHBOURS) {
      const x = monster.x + dx, y = monster.y + dy;
      if (!walkable(map, x, y) || isBlocked(x, y)) continue;
      const cheb = chebyshev(x, y, player.x, player.y);
      const sq = (x - player.x) ** 2 + (y - player.y) ** 2;
      if (cheb < bestCheb || (cheb === bestCheb && sq < bestSq)) {
        best = { x, y };
        bestCheb = cheb;
        bestSq = sq;
      }
    }
    return best ? { type: 'move', x: best.x, y: best.y } : { type: 'wait' };
  }
  const open = [];
  for (const [dx, dy] of NEIGHBOURS) {
    const x = monster.x + dx, y = monster.y + dy;
    if (walkable(map, x, y) && !isBlocked(x, y)) open.push({ x, y });
  }
  if (open.length === 0) return { type: 'wait' };
  const step = rng.pick(open);
  return { type: 'move', x: step.x, y: step.y };
}
