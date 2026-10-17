// Game state and turn loop. Pure: no DOM, no Math.random. Uses the rng, map, fov and rules modules.
import { createRng } from './rng.js';
import { generateMap, isWalkable, WALL, FLOOR, STAIRS } from './map.js';
import { computeFov } from './fov.js';
import { spawnMonsters, spawnItems, spawnTraps, attack, applyItem, monsterStep } from './rules.js';

export const MAX_DEPTH = 5, FOV_RADIUS = 8;

const LOG_KEEP = 50; // lines kept in state.log
const VIEW_LOG = 5; // lines returned by getView
const XP_PER_LEVEL = 10;
const PLAYER_START = { hp: 32, atk: 2, def: 0 };
const POISON_TURNS = 3; // turns of poison a poison monster's melee hit gives the player
const TILE_FG = { [WALL]: '#94a3b8', [FLOOR]: '#475569', [STAIRS]: '#fde047' };
const DIM = '#2a303b';

// Seeds may be numbers or strings (from ?seed=). A string is hashed (FNV-1a) to a 32-bit number.
function seedToNumber(seed) {
  if (typeof seed === 'number' && Number.isFinite(seed)) return seed >>> 0;
  const s = String(seed);
  let h = 0x811c9dc5;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 0x01000193) >>> 0;
  }
  return h;
}

function say(state, msg) {
  state.log.push(msg);
  if (state.log.length > LOG_KEEP) state.log.splice(0, state.log.length - LOG_KEEP);
}

function tileIndex(map, x, y) {
  return y * map.w + x;
}

function monsterAt(state, x, y) {
  return state.monsters.find((m) => m.x === x && m.y === y) || null;
}

function itemAt(state, x, y) {
  return state.items.find((it) => it.x === x && it.y === y) || null;
}

// A random FLOOR tile with no monster and no trap, from the game rng. Null if there is none.
function teleportTarget(state, rng) {
  const { map } = state;
  const taken = new Set([...state.monsters, ...state.traps].map((e) => tileIndex(map, e.x, e.y)));
  const free = [];
  for (let i = 0; i < map.tiles.length; i++) {
    if (map.tiles[i] === FLOOR && !taken.has(i)) free.push(i);
  }
  if (free.length === 0) return null;
  const i = free[rng.int(0, free.length - 1)];
  return { x: i % map.w, y: Math.floor(i / map.w) };
}

function updateFov(state) {
  const p = state.player;
  state.visible = computeFov(state.map, p.x, p.y, FOV_RADIUS);
  for (const i of state.visible) state.explored[i] = true;
}

// Builds a new level at state.depth and puts the player on its start tile.
function buildLevel(state, rng) {
  state.map = generateMap(rng);
  const map = state.map;
  state.player.x = map.start.x;
  state.player.y = map.start.y;
  const occupied = new Set();
  state.monsters = spawnMonsters(rng, map, state.depth, occupied);
  state.items = spawnItems(rng, map, state.depth, occupied);
  state.traps = spawnTraps(rng, map, state.depth, occupied);
  state.explored = new Array(map.w * map.h).fill(false);
  updateFov(state);
}

function gainXp(state, amount) {
  const p = state.player;
  const before = Math.floor(p.xp / XP_PER_LEVEL);
  p.xp += amount;
  const gained = Math.floor(p.xp / XP_PER_LEVEL) - before;
  for (let k = 0; k < gained; k++) {
    p.maxHp += 5;
    p.atk += 1;
  }
  if (gained > 0) {
    p.level = 1 + Math.floor(p.xp / XP_PER_LEVEL);
    say(state, `You reach level ${p.level}.`);
  }
}

function playerAttacks(state, target, rng) {
  const r = attack(state.player, target, rng);
  if (r.killed) {
    state.monsters = state.monsters.filter((m) => m !== target);
    say(state, `You kill the ${target.kind}.`);
    gainXp(state, target.xp);
  } else {
    say(state, `You hit the ${target.kind} for ${r.damage}.`);
  }
}

// Every living monster acts once. Uses the visible set from the last FOV update.
function monsterPhase(state, rng) {
  const p = state.player;
  const occupied = new Set(state.monsters.map((m) => tileIndex(state.map, m.x, m.y)));
  const isBlocked = (x, y) => (x === p.x && y === p.y) || occupied.has(tileIndex(state.map, x, y));
  for (const m of [...state.monsters]) {
    if (m.hp <= 0) continue;
    const step = monsterStep(state.map, m, p, state.visible, isBlocked, rng);
    if (step.type === 'attack') {
      const r = attack(m, p, rng);
      say(state, `The ${m.kind} hits you for ${r.damage}.`);
      if (m.ability === 'poison') p.poison = POISON_TURNS;
      if (p.hp <= 0) return;
    } else if (step.type === 'shoot') {
      const r = attack({ ...m, atk: Math.max(1, m.atk - 1) }, p, rng);
      say(state, `The ${m.kind} shoots you for ${r.damage}.`);
      if (p.hp <= 0) return;
    } else if (step.type === 'move') {
      occupied.delete(tileIndex(state.map, m.x, m.y));
      m.x = step.x;
      m.y = step.y;
      occupied.add(tileIndex(state.map, m.x, m.y));
    }
  }
}

// Every living regen monster below maxHp heals 1 hp.
function regenerate(state) {
  for (const m of state.monsters) {
    if (m.ability === 'regen' && m.hp > 0 && m.hp < m.maxHp) m.hp += 1;
  }
}

// Poison ticks once per turn: 1 hp lost, one turn less to run.
function ticksPoison(state) {
  const p = state.player;
  if (p.poison <= 0 || state.status !== 'playing') return;
  p.hp -= 1;
  p.poison -= 1;
  say(state, 'Poison hurts you.');
}

// The player stands on tile (x, y): a trap there reveals itself and fires, every time. Monsters
// never trigger traps.
function triggerTrap(state, rng) {
  const p = state.player;
  const trap = state.traps.find((t) => t.x === p.x && t.y === p.y);
  if (!trap) return;
  trap.hidden = false;
  if (trap.effect === 'damage') {
    const before = p.hp;
    p.hp = Math.max(1, p.hp - trap.amount);
    say(state, `A ${trap.kind} trap wounds you for ${before - p.hp}.`);
  } else if (trap.effect === 'poison') {
    p.poison = POISON_TURNS;
    say(state, 'A poison needle pricks you.');
  } else if (trap.effect === 'teleport') {
    const dest = teleportTarget(state, rng);
    if (dest) {
      p.x = dest.x;
      p.y = dest.y;
    }
    say(state, 'A teleport trap moves you.');
  }
}

// Ends a turn: monsters act (unless skipped), poison ticks, FOV and explored update, turn goes up,
// death check.
function endTurn(state, rng, monstersAct) {
  if (monstersAct && state.status === 'playing') {
    monsterPhase(state, rng);
    regenerate(state);
  }
  ticksPoison(state);
  updateFov(state);
  state.turn += 1;
  if (state.player.hp <= 0 && state.status === 'playing') {
    state.status = 'dead';
    say(state, 'You die.');
  }
}

export function newGame(seed) {
  const rng = createRng(seedToNumber(seed));
  const state = {
    seed,
    rngState: 0,
    depth: 1,
    map: null,
    player: {
      id: 0, kind: 'player', glyph: '@', color: '#f8fafc', x: 0, y: 0,
      hp: PLAYER_START.hp, maxHp: PLAYER_START.hp, atk: PLAYER_START.atk, def: PLAYER_START.def,
      xp: 0, level: 1, inventory: [], poison: 0,
    },
    monsters: [],
    items: [],
    traps: [],
    visible: new Set(),
    explored: [],
    log: ['Welcome to the dungeon.'],
    turn: 0,
    status: 'playing',
  };
  buildLevel(state, rng);
  state.rngState = rng.state();
  return state;
}

// Applies one action. Mutates and returns state. Ignored unless status is 'playing'.
export function act(state, action) {
  if (state.status !== 'playing' || !action) return state;
  const rng = createRng(state.rngState);
  const p = state.player;
  const map = state.map;
  let takesTurn = false;
  let monstersAct = true;

  switch (action.type) {
    case 'move': {
      const { dx, dy } = action;
      const ok = [dx, dy].every((v) => Number.isInteger(v) && v >= -1 && v <= 1) && !(dx === 0 && dy === 0);
      if (!ok) break;
      const nx = p.x + dx, ny = p.y + dy;
      const target = monsterAt(state, nx, ny);
      if (target) {
        playerAttacks(state, target, rng);
        takesTurn = true;
      } else if (isWalkable(map, nx, ny)) {
        p.x = nx;
        p.y = ny;
        takesTurn = true;
        triggerTrap(state, rng);
      } else {
        say(state, 'A wall blocks the way.');
      }
      break;
    }
    case 'wait':
      takesTurn = true;
      break;
    case 'pickup': {
      const item = itemAt(state, p.x, p.y);
      if (!item) {
        say(state, 'Nothing to pick up here.');
      } else {
        state.items = state.items.filter((it) => it !== item);
        p.inventory.push(item);
        say(state, `You pick up the ${item.kind}.`);
        takesTurn = true;
      }
      break;
    }
    case 'use': {
      const i = action.index;
      if (!Number.isInteger(i) || i < 0 || i >= p.inventory.length) {
        say(state, 'No item in that slot.');
        break;
      }
      const [item] = p.inventory.splice(i, 1);
      say(state, applyItem(p, item));
      takesTurn = true;
      break;
    }
    case 'descend': {
      if (map.tiles[tileIndex(map, p.x, p.y)] !== STAIRS) {
        say(state, 'There are no stairs here.');
        break;
      }
      takesTurn = true;
      monstersAct = false;
      if (state.depth >= MAX_DEPTH) {
        state.status = 'won';
        say(state, 'You take the last stairs and escape the dungeon.');
      } else {
        state.depth += 1;
        buildLevel(state, rng);
        say(state, `You descend to depth ${state.depth}.`);
      }
      break;
    }
    default:
      break;
  }

  if (takesTurn) endTurn(state, rng, monstersAct);
  state.rngState = rng.state();
  return state;
}

export function getView(state) {
  const { map, player: p, monsters, items, traps, visible, explored } = state;
  const monsterBy = new Map(monsters.map((m) => [tileIndex(map, m.x, m.y), m]));
  const itemBy = new Map(items.map((it) => [tileIndex(map, it.x, it.y), it]));
  const trapBy = new Map(traps.map((t) => [tileIndex(map, t.x, t.y), t]));
  const cells = [];
  for (let i = 0; i < map.w * map.h; i++) {
    const x = i % map.w, y = Math.floor(i / map.w);
    if (p.x === x && p.y === y) {
      cells.push({ ch: p.glyph, fg: p.color, bg: null });
    } else if (visible.has(i) && monsterBy.has(i)) {
      const m = monsterBy.get(i);
      cells.push({ ch: m.glyph, fg: m.color, bg: null });
    } else if (visible.has(i) && itemBy.has(i)) {
      const it = itemBy.get(i);
      cells.push({ ch: it.glyph, fg: it.color, bg: null });
    } else if (visible.has(i) && trapBy.has(i) && !trapBy.get(i).hidden) {
      const t = trapBy.get(i);
      cells.push({ ch: t.glyph, fg: t.color, bg: null });
    } else if (visible.has(i)) {
      const t = map.tiles[i];
      cells.push({ ch: t, fg: TILE_FG[t] || DIM, bg: null });
    } else if (explored[i]) {
      cells.push({ ch: map.tiles[i], fg: DIM, bg: null });
    } else {
      cells.push({ ch: ' ', fg: DIM, bg: null });
    }
  }
  return {
    w: map.w,
    h: map.h,
    cells,
    hud: {
      hp: p.hp, maxHp: p.maxHp, atk: p.atk, def: p.def, depth: state.depth,
      level: p.level, xp: p.xp, turn: state.turn, poison: p.poison,
    },
    log: state.log.slice(-VIEW_LOG),
    status: state.status,
    player: { x: p.x, y: p.y },
    inventory: p.inventory.map((it) => ({
      kind: it.kind, glyph: it.glyph, color: it.color, effect: it.effect, amount: it.amount,
    })),
    visibleMonsters: state.monsters
      .filter((m) => m.hp > 0 && visible.has(tileIndex(map, m.x, m.y)))
      .map((m) => ({
        kind: m.kind, glyph: m.glyph, color: m.color, hp: m.hp, maxHp: m.maxHp, ability: m.ability,
      })),
    traps: traps
      .filter((t) => !t.hidden && visible.has(tileIndex(map, t.x, t.y)))
      .map((t) => ({ kind: t.kind, glyph: t.glyph, color: t.color, x: t.x, y: t.y })),
  };
}
