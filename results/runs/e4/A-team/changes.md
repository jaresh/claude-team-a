# Change log

One line per edit to a shared file: date, teammate, file, function or row, what changed.

- 2026-10-17, traps, game/src/data/traps.js, TRAPS: new table with spike (damage 3), poison needle (poison), teleport (teleport).
- 2026-10-17, traps, game/src/core/rules.js, spawnTraps: new function, 1 + depth hidden traps; imports TRAPS.
- 2026-10-17, traps, game/src/core/game.js, newGame/buildLevel/act/getView: traps state, triggerTrap on player move, trap cells and view.traps.
- 2026-10-17, traps, game/src/data/traps.js, TRAPS spike row: amount 3 -> 2 (e2 balance: win rate was 0.135 with spike 3, below 15%).
- 2026-10-17, traps, game/src/core/game.js, PLAYER_START: hp 30 -> 32 (e2 balance: win rate 0.150 with spike 2 alone, on the boundary; now 0.165, mean depth 4.00).

