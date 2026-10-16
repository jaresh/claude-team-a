// Fake stand-in for core/game.js so the UI can be built before the core exists.
// Same three exports and the same View shape. This is not game logic: one room with a
// pillar, one rat, one potion. Visibility is a square radius, not real FOV.
// main.js imports this file until core/game.js lands (wave 2).

export const MAX_DEPTH = 5, FOV_RADIUS = 8;

const W = 24, H = 14;
const START = { x: 3, y: 3 };
const STAIRS = { x: 21, y: 11 };
const TILE_FG = { '#': '#94a3b8', '.': '#475569', '>': '#fde047' };
const DIM = '#2a303b';
const LOG_KEEP = 50;

const idx = (x, y) => y * W + x;
const inBounds = (x, y) => x >= 0 && y >= 0 && x < W && y < H;
const isWalkable = (map, x, y) => inBounds(x, y) && (map.tiles[idx(x, y)] === '.' || map.tiles[idx(x, y)] === '>');
const cheb = (ax, ay, bx, by) => Math.max(Math.abs(ax - bx), Math.abs(ay - by));

function buildMap() {
  const tiles = [];
  for (let y = 0; y < H; y++) {
    for (let x = 0; x < W; x++) {
      const edge = x === 0 || y === 0 || x === W - 1 || y === H - 1;
      const pillar = x >= 9 && x <= 10 && y >= 5 && y <= 7;
      tiles.push(edge || pillar ? '#' : '.');
    }
  }
  tiles[idx(STAIRS.x, STAIRS.y)] = '>';
  return {
    w: W, h: H, tiles,
    rooms: [{ x: 1, y: 1, w: W - 2, h: H - 2 }],
    start: { ...START }, stairs: { ...STAIRS },
  };
}

function say(state, msg) {
  state.log.push(msg);
  if (state.log.length > LOG_KEEP) state.log.splice(0, state.log.length - LOG_KEEP);
}

function enterLevel(state) {
  state.map = buildMap();
  state.player.x = START.x;
  state.player.y = START.y;
  const hp = 3 + state.depth - 1;
  state.monsters = [{ id: 1, kind: 'rat', glyph: 'r', color: '#b9a37e', x: 16, y: 4, hp, maxHp: hp, atk: 1, def: 0, xp: 1 }];
  state.items = [{ id: 2, kind: 'potion', glyph: '!', color: '#ff5fa2', effect: 'heal', amount: 8, x: 5, y: 8 }];
  state.explored = new Array(W * H).fill(false);
}

function updateFov(state) {
  const p = state.player;
  const visible = new Set();
  for (let y = p.y - FOV_RADIUS; y <= p.y + FOV_RADIUS; y++) {
    for (let x = p.x - FOV_RADIUS; x <= p.x + FOV_RADIUS; x++) {
      if (!inBounds(x, y)) continue;
      visible.add(idx(x, y));
      state.explored[idx(x, y)] = true;
    }
  }
  state.visible = visible;
}

const monsterAt = (state, x, y) => state.monsters.find((m) => m.x === x && m.y === y);
const itemAt = (state, x, y) => state.items.find((it) => it.x === x && it.y === y);

function attackMonster(state, m) {
  const p = state.player;
  const dmg = Math.max(1, p.atk + (state.turn % 3) - m.def);
  m.hp -= dmg;
  if (m.hp > 0) {
    say(state, `You hit the ${m.kind} for ${dmg}.`);
    return;
  }
  state.monsters = state.monsters.filter((x) => x !== m);
  say(state, `You kill the ${m.kind}.`);
  p.xp += m.xp;
  const level = 1 + Math.floor(p.xp / 10);
  while (p.level < level) {
    p.level += 1;
    p.maxHp += 5;
    p.atk += 1;
    say(state, `You reach level ${p.level}.`);
  }
}

function endTurn(state) {
  const p = state.player;
  for (const m of [...state.monsters]) {
    if (p.hp <= 0) break;
    if (!state.visible.has(idx(m.x, m.y))) continue;
    if (cheb(m.x, m.y, p.x, p.y) <= 1) {
      const dmg = Math.max(1, m.atk - p.def);
      p.hp -= dmg;
      say(state, `The ${m.kind} hits you for ${dmg}.`);
      if (p.hp <= 0) {
        p.hp = 0;
        state.status = 'dead';
        say(state, 'You die.');
      }
      continue;
    }
    let best = null;
    let bestD = cheb(m.x, m.y, p.x, p.y);
    for (let dy = -1; dy <= 1; dy++) {
      for (let dx = -1; dx <= 1; dx++) {
        if (dx === 0 && dy === 0) continue;
        const nx = m.x + dx, ny = m.y + dy;
        if (!isWalkable(state.map, nx, ny)) continue;
        if ((nx === p.x && ny === p.y) || monsterAt(state, nx, ny)) continue;
        const d = cheb(nx, ny, p.x, p.y);
        if (d < bestD) { bestD = d; best = [nx, ny]; }
      }
    }
    if (best) { m.x = best[0]; m.y = best[1]; }
  }
  state.turn += 1;
  updateFov(state);
}

export function newGame(seed) {
  const state = {
    seed, rngState: 0, depth: 1, map: null,
    player: {
      id: 0, kind: 'player', glyph: '@', color: '#f8fafc', x: START.x, y: START.y,
      hp: 12, maxHp: 12, atk: 3, def: 1, xp: 0, level: 1, inventory: [],
    },
    monsters: [], items: [], visible: new Set(), explored: [],
    log: ['Mock dungeon. Find the > stairs.'],
    turn: 0, status: 'playing',
  };
  enterLevel(state);
  updateFov(state);
  return state;
}

// Every action that is accepted writes at least one log line. Blocked moves and
// invalid actions cost no turn.
export function act(state, action) {
  if (state.status !== 'playing') return state;
  const p = state.player;
  let takesTurn = false;
  switch (action.type) {
    case 'move': {
      const nx = p.x + action.dx, ny = p.y + action.dy;
      const target = monsterAt(state, nx, ny);
      if (target) {
        attackMonster(state, target);
        takesTurn = true;
      } else if (isWalkable(state.map, nx, ny)) {
        p.x = nx;
        p.y = ny;
        say(state, 'You move.');
        takesTurn = true;
      } else {
        say(state, 'A wall blocks the way.');
      }
      break;
    }
    case 'wait':
      say(state, 'You wait.');
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
      const item = p.inventory[action.index];
      if (!item) {
        say(state, 'No item in that slot.');
      } else {
        p.inventory.splice(action.index, 1);
        p.hp = Math.min(p.maxHp, p.hp + item.amount);
        say(state, `You drink the ${item.kind}. +${item.amount} hp.`);
        takesTurn = true;
      }
      break;
    }
    case 'descend': {
      if (state.map.tiles[idx(p.x, p.y)] !== '>') {
        say(state, 'No stairs here.');
        break;
      }
      if (state.depth >= MAX_DEPTH) {
        state.status = 'won';
        say(state, 'You take the last stairs. You win.');
        break;
      }
      state.depth += 1;
      enterLevel(state);
      say(state, `You go down to depth ${state.depth}.`);
      takesTurn = true;
      break;
    }
    default:
      say(state, `Unknown action: ${action.type}.`);
  }
  if (takesTurn) endTurn(state);
  return state;
}

export function getView(state) {
  const { map, player: p, monsters, items, visible, explored } = state;
  const cells = [];
  for (let i = 0; i < map.w * map.h; i++) {
    const x = i % map.w;
    const y = (i - x) / map.w;
    const seen = visible.has(i);
    if (p.x === x && p.y === y) {
      cells.push({ ch: p.glyph, fg: p.color, bg: null });
      continue;
    }
    const m = seen ? monsterAt(state, x, y) : undefined;
    if (m) { cells.push({ ch: m.glyph, fg: m.color, bg: null }); continue; }
    const it = seen ? itemAt(state, x, y) : undefined;
    if (it) { cells.push({ ch: it.glyph, fg: it.color, bg: null }); continue; }
    const tile = map.tiles[i];
    if (seen) cells.push({ ch: tile, fg: TILE_FG[tile], bg: null });
    else if (explored[i]) cells.push({ ch: tile, fg: DIM, bg: null });
    else cells.push({ ch: ' ', fg: DIM, bg: null });
  }
  return {
    w: map.w,
    h: map.h,
    cells,
    player: { x: p.x, y: p.y },
    inventory: p.inventory.map((it) => ({
      kind: it.kind, glyph: it.glyph, color: it.color, effect: it.effect, amount: it.amount,
    })),
    hud: {
      hp: p.hp, maxHp: p.maxHp, atk: p.atk, def: p.def, depth: state.depth,
      level: p.level, xp: p.xp, turn: state.turn,
    },
    log: state.log.slice(-5),
    status: state.status,
  };
}
