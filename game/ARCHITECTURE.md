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

### e1: View additions (owner: view)

`getView(state)` also returns:

- `player: { x, y }`: the player's tile.
- `inventory: [{ kind, glyph, color, effect, amount }]`, in inventory order. Entry `i` is the item
  that `{ type: 'use', index: i }` uses.

Nothing else in `game.js` changes.

### e1: camera and inventory panel (owner: screen)

`game/src/ui/camera.js`:

```js
export const MIN_CELL = 16; // css px
export function cameraWindow(view, cols, rows) // -> { x0, y0, cols, rows }
```

- `cols` becomes `Math.min(cols, view.w)`, `rows` becomes `Math.min(rows, view.h)`.
- The window is centred on `view.player`: `x0 = player.x - Math.floor(cols / 2)`, clamped to
  `0 .. view.w - cols`; `y0` the same way with `rows` and `view.h`.

`render.js` draws only the camera window:

- `cols = Math.min(view.w, Math.floor(cssWidth / MIN_CELL))`, `cell = Math.floor(cssWidth / cols)`,
  `rows = Math.min(view.h, 15)`. It sets `canvas.dataset.cell`, `canvas.dataset.cols` and
  `canvas.dataset.rows` to those numbers.
- It fills an inventory panel, the element with `id="inventory"`: one button per item with
  `data-action="use"` and `data-index="<i>"`, labelled `<i + 1> <glyph> <kind>`, or the text
  `Inventory empty`.

Other UI changes: `index.html` gets the `#inventory` element and loses the `Use 1` button;
`input.js` handles taps on the inventory buttons (keys `1`-`9` keep working); `mock-game.js`
returns `player` and `inventory` in its view too.

### e2: balance (owner: tuner)

Targets, checked by `game/accept/e2-balance.test.js` (the bot on `game/sim/seeds-200.txt`,
5000-turn cap):

- win rate between 15% and 40%;
- mean depth reached at least 3.0;
- no monster kind causes more than 40% of deaths.

Allowed changes, each logged in the team change log:

- values in existing rows of `data/monsters.js` and `data/items.js`, and new rows appended at
  the end;
- the spawn counts in `core/rules.js` (`3 + 2 * depth` and `2 + Math.floor(depth / 2)`);
- `PLAYER_START` and the level-up gains in `core/game.js`.

Not allowed: `game/sim/bot.mjs`, `game/accept/`, any other logic.

### e2: end screen and HP bar (owner: hud)

`game/src/ui/hud.js`:

```js
export function endMessage(view) // -> string | null
//   status 'playing' -> null
//   'dead' -> `You died on depth ${view.hud.depth} after ${view.hud.turn} turns.`
//   'won'  -> `You won! Depth ${view.hud.depth} in ${view.hud.turn} turns.`
export function hpColor(hp, maxHp) // -> '#3fb950' if hp / maxHp > 0.5,
//                                       '#d29922' if > 0.25, else '#f85149'
```

- `index.html` gets an HP bar, `id="hpbar"`, whose filled inner part is `hp / maxHp` wide, and an
  end panel, `id="end"`, hidden while playing, holding the end message and a New game button
  (the same action as the existing New game button).
- `render.js` colours and sizes the HP bar with `hpColor`, and shows `#end` with
  `endMessage(view)` when it isn't null, hidden otherwise.
- The empty-inventory text spans the panel's full width (in e1 it wraps onto two lines).

### e3: monster abilities (owner: abilities)

- **Data.** Every `MONSTERS` row gets `ability`: `null`, `'regen'`, `'poison'` or `'ranged'`.
  Each of the three abilities is used by at least one kind, and one new kind is appended (at
  least 7 kinds). `spawnMonsters` copies `ability` onto each monster.
- **`monsterStep`.** A monster with `ability: 'ranged'` whose tile is in `visible`, at Chebyshev
  distance 2 to 4 from the player, returns `{ type: 'shoot' }`. Nothing else changes.
- **`game.js`.**
  - `shoot`: an attack on the player with the monster's `atk` lowered by 1 (at least 1); log
    `The <kind> shoots you for <n>.`
  - `regen`: after each monster phase, every living `regen` monster below `maxHp` gains 1 hp.
  - `poison`: when a `poison` monster damages the player in melee, `player.poison = 3`. At the
    end of every turn with `player.poison > 0`, the player loses 1 hp, `poison` goes down by 1, and
    the log says `Poison hurts you.` Dying from poison is an ordinary death.
  - `getView` adds `hud.poison` (turns left, 0 when none) and
    `visibleMonsters: [{ kind, glyph, color, hp, maxHp, ability }]`: living monsters on visible
    tiles.
- **Balance.** The e2 targets still hold (`game/accept/e2-balance.test.js`), with the changes the
  e2 balance section allows.

### e3: monster legend (owner: legend)

`game/src/ui/legend.js`:

```js
export function legendRows(view) // -> [{ text, color }], one per view.visibleMonsters entry
//   text: `${glyph} ${kind} ${hp}/${maxHp}`, plus ` ${ability}` when ability isn't null
export function poisonLabel(view) // -> `Poisoned (${view.hud.poison})` when > 0, else null
```

- `index.html` gets a legend panel, `id="legend"`; `render.js` fills it with one line per
  `legendRows` entry in that entry's colour, and shows `poisonLabel` next to the HUD when it isn't
  null.
- `mock-game.js` returns `visibleMonsters` and `hud.poison` too.

### e4: traps (owner: traps)

`game/src/data/traps.js`:

```js
export const TRAPS = [
  { kind: 'spike', glyph: '^', color: '#c9d1d9', effect: 'damage', amount: 3, minDepth: 1 },
  // ... at least 3 kinds; effect is 'damage', 'poison' or 'teleport', each used at least once
];
// Trap: { id, kind, glyph, color, effect, amount, x, y, hidden }
```

- **`rules.js`.** `export function spawnTraps(rng, map, depth, occupied) // -> Trap[]` makes
  `1 + depth` traps from kinds with `minDepth <= depth`, placed like `spawnItems` (FLOOR, not in
  `occupied`, never `map.start` or `map.stairs`; adds each index to `occupied`), all with
  `hidden: true`. Its `id` values don't collide with monster or item ids on the level.
- **`game.js`.** `GameState` gets `traps: Trap[]`, spawned after monsters and items with the same
  `occupied` set, on every level (`newGame` and `descend`). When the player moves onto a trap's
  tile, before the monster phase, the trap sets `hidden: false` and fires (every time, not only
  the first):
  - `damage`: the player loses `amount` hp but never drops below 1; log
    `A <kind> trap wounds you for <n>.` (never "hits you": the bot reads that phrase for killers);
  - `poison`: `player.poison = 3`, then poison ticks as in e3; log `A poison needle pricks you.`;
  - `teleport`: the player moves to a random FLOOR tile with no monster and no trap, chosen with
    the game's rng; log `A teleport trap moves you.`

  Monsters never trigger traps.
- **`getView`.** Cell order: player, monster, item, trap, tile. A trap shows on a visible tile
  only when it is not hidden. `View` adds `traps: [{ kind, glyph, color, x, y }]`: traps that are
  not hidden, on visible tiles.
- **Balance.** The e2 targets still hold (`game/accept/e2-balance.test.js`). Besides the changes
  the e2 balance section allows, the `amount` values in `TRAPS` may change (the trap count
  stays `1 + depth`); log each change (rule 13).

### e4: help overlay (owner: help)

`game/src/ui/help.js`:

```js
export const HELP_KEYS // -> [{ keys, action }], at least: move (arrows, WASD, hjkl, yubn),
//   wait (.), pick up (g), descend (>), use item (1-9), help (?), close help (Esc)
export function glyphRows(view) // -> [{ glyph, color, name }]:
//   { glyph: '@', name: 'you' }, then { glyph: '>', name: 'stairs down' }, then one row per
//   trap kind in view.traps, in first-seen order, with that trap's glyph and color and
//   name `${kind} trap`. Colors: '@' '#f8fafc' and '>' '#fde047', as getView draws them.
```

- `input.js`: key `?` -> `{ type: 'help' }`, key `Escape` -> `{ type: 'close' }`, and a button
  with `data-action="help"` -> `{ type: 'help' }`.
- `index.html` gets a `?` button (`data-action="help"`) and a help panel, `id="help"`, hidden at
  start. `main.js` handles `help` (toggles the panel) and `close` (hides it) itself and never
  passes them to `act`. `render.js` fills the panel with one line per `HELP_KEYS` entry and one
  per `glyphRows(view)` row, in that row's colour.
- `mock-game.js` returns `traps` in its view too (at least one trap, for the panel).

### e5: score and stats (owner: score)

`game/src/core/score.js`:

```js
export function score(stats, status) // -> integer, never below 0:
//   100 * stats.deepest + 10 * (sum of the stats.kills values) + 5 * stats.itemsUsed
//   - 2 * stats.trapsTriggered + (status === 'won' ? 500 : 0)
```

- `GameState` gets `stats: { kills: {}, itemsUsed: 0, trapsTriggered: 0, deepest: 1,
  damageTaken: 0 }`, set by `newGame` and kept across levels. `game.js` updates it:
  - `kills[kind] += 1` when the player kills a monster of that kind (missing kinds start at 0);
  - `itemsUsed += 1` when a `use` action consumes an item;
  - `trapsTriggered += 1` each time a trap fires;
  - `deepest` is the deepest depth reached (`descend` raises it);
  - `damageTaken` adds every hp the player loses: melee, shots, traps and poison.
- `getView` adds `stats` (a deep copy: changing it, `kills` included, doesn't change the state) and
  `score: score(state.stats, state.status)`.
- Nothing else changes; the e2 balance is unaffected.

### e5: run summary and high scores (owner: summary)

`game/src/ui/scores.js`:

```js
export const MAX_SCORES = 5, SCORES_KEY = 'roguelike-scores';
export function addScore(list, entry) // -> a new list; `list` is not changed.
//   entry: { score, depth, turns, seed, won }. Sorted by score, highest first; equal scores:
//   fewer turns first. At most MAX_SCORES entries.
export function loadScores(storage) // storage: { getItem, setItem } (localStorage) -> list;
//   [] when the key is missing or its value isn't a JSON array
export function saveScores(storage, list) // writes JSON.stringify(list) under SCORES_KEY
export function summaryRows(view) // -> [{ label, value }] in this order, values numbers:
//   'Score' view.score, 'Depth reached' view.stats.deepest, 'Turns' view.hud.turn,
//   'Kills' (sum of view.stats.kills), 'Items used', 'Traps triggered', 'Damage taken'
```

- `index.html` gets a high-score list, `id="scores"`, inside the end panel (`#end`).
  `render.js` shows the `summaryRows` lines and the high scores in `#end` when the game has
  ended. `main.js` adds each finished game once (when `status` leaves `'playing'`) with
  `addScore`, using `{ score, depth: stats.deepest, turns: hud.turn, seed, won }`, and saves
  it; storage access is wrapped in try/catch, so the game works without it.
- `mock-game.js` returns `stats` and `score` in its view too.

### `sim/bot.mjs` (owner: sim, wave 3)

`node game/sim/bot.mjs --seeds <file> --out <file>` plays each seed with a simple greedy policy
until dead, won or 5000 turns, and writes per-seed stats plus a summary (win rate, mean depth,
mean turns, deaths by monster kind) as JSON.
