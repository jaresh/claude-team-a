# Change log

One line per edit to a shared file: date, teammate, file, function or row, what changed.

- 2026-10-17, help, game/src/ui/input.js, keyToAction/buttonToAction, added `?` -> help, Escape -> close, data-action help/close.
- 2026-10-17, help, game/src/ui/render.js, render/renderHelp, fills #help-list from HELP_KEYS and glyphRows(view) (needs view.traps from getView).
- 2026-10-17, help, game/src/ui/mock-game.js, enterLevel/getView, adds one spike trap and view.traps.
- 2026-10-17, help, game/src/main.js, bindInput handler, help toggles #help, close hides it; neither reaches act().
- 2026-10-17, help, game/index.html, controls/CSS, adds ? button, hidden #help panel with #help-list, hint text.
- 2026-10-17, help, game/src/ui/help.js (new), HELP_KEYS and glyphRows.
- 2026-10-17, help, game/test/help.test.js (new), 4 tests.
- 2026-10-17, traps, game/src/data/traps.js (new), TRAPS: spike (damage 3, minDepth 1), needle (poison, minDepth 2), rune (teleport, minDepth 3).
- 2026-10-17, traps, game/src/data/traps.js, TRAPS spike row: amount 3 -> 2 (win rate 0.12 -> 0.14 after the trap spawns; e2 floor is 15%).
- 2026-10-17, traps, game/src/core/game.js, PLAYER_START: hp 30 -> 34 (win rate still under 15% with spike at 2; e2 balance now passes).
- 2026-10-17, traps, game/src/core/rules.js, spawnTraps (new): 1 + depth hidden traps, placed by spawnFrom after items.
- 2026-10-17, traps, game/src/core/game.js, fireTrap/teleportSpots/buildLevel/act move/getView: traps spawn per level, fire on step, view.traps and trap cells.
- 2026-10-17, traps, game/test/traps.test.js (new), 9 tests.
