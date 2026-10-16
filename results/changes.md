# Change log

One line per edit to a shared generator, config or table (rule 13). Append at the end.

| Date | Teammate | File | Function or row | What changed |
|---|---|---|---|---|
| 2026-10-16 | view | game/src/core/game.js | getView | added `player` {x,y} and `inventory` entries (e1 View additions) |
| 2026-10-16 | tuner | game/src/data/monsters.js | goblin | atk 3 -> 2 |
| 2026-10-16 | tuner | game/src/data/monsters.js | goblin | hp 8 -> 6 |
| 2026-10-16 | tuner | game/src/data/monsters.js | orc | atk 4 -> 3 |
| 2026-10-16 | tuner | game/src/data/monsters.js | orc | hp 14 -> 10 |
| 2026-10-16 | tuner | game/src/data/items.js | potion | heal amount 8 -> 12 |
| 2026-10-16 | tuner | game/src/core/rules.js | spawnMonsters | count 3 + 2*depth -> 3 + depth |
| 2026-10-16 | tuner | game/src/core/rules.js | spawnItems | count 2 + floor(depth/2) -> 3 + floor(depth/2) |
| 2026-10-16 | tuner | game/src/core/game.js | PLAYER_START | hp 20 -> 40 (set in two steps, 20 -> 30 -> 40; final value logged) |
| 2026-10-16 | tuner | game/test/rules.test.js | spawn count tests | assertions updated to 3 + depth and 3 + floor(depth/2) (unit test, not a table) |
| 2026-10-16 | lead | game/index.html | #end panel | moved after .controls (smoke taps the first 4 buttons; hidden New game was first) and made a fixed centred overlay |
