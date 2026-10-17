# Change log

One line per edit to a shared file: date, teammate, file, function or row, what changed.

2026-10-17 traps game/src/data/traps.js (new) TRAPS: created with spike (damage 3), poison needle (poison 3), teleport.
2026-10-17 traps game/src/data/traps.js TRAPS spike row: amount 3 -> 2 (e2 win rate was 0.120 with 3; floor is 0.15).
2026-10-17 traps game/src/core/rules.js spawnTraps: new function, uses spawnFrom.
2026-10-17 traps game/src/core/game.js: state.traps, buildLevel, triggerTrap, getView trap cell and View.traps.
2026-10-17 lead game/src/core/game.js PLAYER_START hp 30 -> 34 (e2 win rate 0.140 -> 0.175 with traps).
