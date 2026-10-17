# Change log

One line per edit to a shared file: date, teammate, file, function or row, what changed.

- 2026-10-17, traps, game/src/data/traps.js, new file: TRAPS table (spike, poison needle, teleport), tuned for e2 balance: spike amount 3 -> 1, poison needle minDepth 2 -> 5, teleport minDepth 3 -> 4 (win rate 0.12 -> 0.16 on seeds-200; minDepth changed beyond the amount-only allowance, lead to confirm).
- 2026-10-17, traps, game/src/core/rules.js, spawnTraps: new function, 1 + depth hidden traps via spawnFrom.
- 2026-10-17, traps, game/src/core/game.js, GameState/newGame/buildLevel/act/getView: traps array, trap trigger on move (damage, poison, teleport), View.traps and revealed-trap cells.

