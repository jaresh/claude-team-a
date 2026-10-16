# Game architecture and contracts

A turn-based roguelike in plain JavaScript: ES modules, no build step, no dependencies.

- **Core** (`game/src/core/`, `game/src/data/`) is pure logic. No DOM, no `Math.random`. It runs
  in Node and in the browser.
- **UI** (`game/index.html`, `game/src/main.js`, `game/src/ui/`) is the only code that touches
  the DOM.

## Commands

| What | Command |
|---|---|
| All tests | `npm test` |
| One test file | `node --test game/test/<module>.test.js` |
| Play locally | `npm run serve`, then open http://localhost:8000/game/ |

## Conventions

- Coordinates are integers: `x` is the column, `y` the row. Tile index `i = y * w + x`.
- A direction is `dx, dy`, each in -1..1 (8 directions). Distance is Chebyshev: `max(|dx|, |dy|)`.
- All randomness goes through the `rng` object passed in.
- Tests use `node:test` and `node:assert/strict`, one file per module in `game/test/`.
- Each module owner edits only their own files. Shared files (`package.json`, this file, data
  tables) follow CLAUDE.md rules 13-14.

## Modules

### `core/rng.js` (owner: world)

```js
export function createRng(seed) // -> Rng
// Rng: { next() -> float in [0, 1), int(min, max) -> integer, both ends inclusive,
//        pick(array) -> one element, state() -> integer internal state }
```

mulberry32. The same seed gives the same sequence. `createRng(rng.state())` continues the
sequence exactly where `rng` is.

### `core/map.js` (owner: world)

```js
export const WALL = '#', FLOOR = '.', STAIRS = '>';
export function generateMap(rng, opts = {}) // -> GameMap
// opts: { w = 60, h = 30, maxRooms = 12, minRoom = 4, maxRoom = 10 }
// GameMap: { w, h, tiles: string[] (length w*h), rooms: [{x, y, w, h}], start: {x, y}, stairs: {x, y} }
export function inBounds(map, x, y)   // -> bool
export function isWalkable(map, x, y) // -> bool: in bounds and FLOOR or STAIRS
export function isOpaque(map, x, y)   // -> bool: WALL or out of bounds
```

Rooms don't overlap and are joined by L-shaped corridors, so every FLOOR tile and the stairs are
reachable from `start`. The map border is wall. `start` is in the first room, `stairs` in the last.

### `core/fov.js` (owner: world)

```js
export function computeFov(map, x, y, radius) // -> Set<number> of visible tile indices
```

Includes the origin. Walls that are seen are included; tiles behind walls are not. Shadowcasting
or ray casting, either is fine.

### `data/monsters.js`, `data/items.js` (owner: rules)

```js
export const MONSTERS = [
  { kind: 'rat', glyph: 'r', color: '#b9a37e', hp: 3, atk: 1, def: 0, xp: 1, minDepth: 1 },
  // ... at least 5 kinds spread over depths 1-5
];
export const ITEMS = [
  { kind: 'potion', glyph: '!', color: '#ff5fa2', effect: 'heal', amount: 8, minDepth: 1 },
  // ... at least 3 kinds; effect is 'heal' (+amount hp, capped at maxHp),
  //     'atk' (+amount atk, permanent) or 'def' (+amount def, permanent)
];
```

Tables only grow by appending rows at the end (rule 14).

### `core/rules.js` (owner: rules)

```js
// Entity: { id, kind, glyph, color, x, y, hp, maxHp, atk, def, xp }
// Item:   { id, kind, glyph, color, effect, amount, x, y }
export function spawnMonsters(rng, map, depth, occupied) // -> Entity[]
export function spawnItems(rng, map, depth, occupied)    // -> Item[]
export function attack(attacker, defender, rng)          // -> { damage, killed }
export function applyItem(player, item)                  // -> message string
export function monsterStep(map, monster, player, visible, isBlocked, rng)
//   -> { type: 'attack' } | { type: 'move', x, y } | { type: 'wait' }
```

- `occupied` is a `Set` of tile indices. Spawns go on FLOOR tiles not in `occupied`, never on
  `map.start` or `map.stairs`, and add their own index to `occupied`.
- `spawnMonsters` makes `3 + 2 * depth` monsters from kinds with `minDepth <= depth`.
  `spawnItems` makes `2 + Math.floor(depth / 2)` items the same way.
- `id` values are unique numbers within one level.
- `attack`: `damage = Math.max(1, attacker.atk + rng.int(0, 2) - defender.def)`; subtracts it
  from `defender.hp`; `killed` is `defender.hp <= 0`.
- `monsterStep` is pure (mutates nothing). If the monster's tile is in `visible`: attack when
  adjacent to the player, else move to the adjacent walkable tile, with `!isBlocked(x, y)`, that
  is closest to the player. Otherwise a random walkable, unblocked step, or wait.

### `core/game.js` (owner: game, wave 2)

```js
export const MAX_DEPTH = 5, FOV_RADIUS = 8;
export function newGame(seed) // -> GameState
export function act(state, action) // -> GameState (mutates and returns it)
export function getView(state) // -> View
// GameState: { seed, rngState, depth, map, player, monsters, items, visible, explored,
//              log: string[], turn, status: 'playing' | 'dead' | 'won' }
//   player: Entity plus { inventory: Item[], level }
//   visible: Set<number>; explored: boolean[] (length w*h)
// action: { type: 'move', dx, dy } (moving into a monster attacks it) | { type: 'wait' }
//       | { type: 'pickup' } | { type: 'use', index } | { type: 'descend' }
// View: { w, h, cells: [{ ch, fg, bg }] (length w*h),
//         hud: { hp, maxHp, atk, def, depth, level, xp, turn }, log: string[] (last 5), status }
```

- `act` ignores actions unless `status` is `'playing'`. It rebuilds the rng with
  `createRng(state.rngState)` and saves `rng.state()` back, so the state stays plain data.
- After a turn-taking action, each living monster runs `monsterStep`; dead monsters are removed
  and give their xp; every 10 xp the player levels up (+5 maxHp, +1 atk). Then FOV and
  `explored` update and `turn` goes up by one. Player hp at 0 or below: `status = 'dead'`.
- `descend` works only on STAIRS. On `MAX_DEPTH` it sets `status = 'won'`; otherwise it builds
  the next level and keeps the player's stats and inventory.
- `getView` cell order: player, then monster, then item, then tile. Visible tiles show their real
  glyph; explored but not visible tiles show the tile only, dimmed; unexplored tiles are `' '`.

### UI (owner: ui)

Files: `game/index.html`, `game/src/main.js`, `game/src/ui/render.js`, `game/src/ui/input.js`,
`game/src/ui/mock-game.js`.

- `render.js`: `export function render(canvas, view, hudEl, logEl)` draws the cells on a canvas
  (monospace, scaled to fit the width; playable on a 360 px wide phone) and fills the HUD and log.
- `input.js`: `export function bindInput(root, onAction)`: keyboard (arrows, WASD, hjkl and yubn
  diagonals, `.` wait, `g` pick up, `>` descend, `1`-`9` use item) and an on-screen d-pad with
  buttons for touch.
- `main.js` wires `newGame` / `act` / `getView` to the UI, with a New game button and the seed
  from `?seed=` in the URL.
- Until `core/game.js` exists, `main.js` imports `ui/mock-game.js` (the same three exports with
  fake data). The game owner switches that import in wave 2.

### `sim/bot.mjs` (owner: sim, wave 3)

`node game/sim/bot.mjs --seeds <file> --out <file>` plays each seed with a simple greedy policy
until dead, won or 5000 turns, and writes per-seed stats plus a summary (win rate, mean depth,
mean turns, deaths by monster kind) as JSON.
