# Handoff: traps

## Done

- `game/src/data/traps.js` (new): TRAPS with three rows, `spike` (damage, amount 2, minDepth 1), `needle` (poison, minDepth 2), `rune` (teleport, minDepth 3).
- `game/src/core/rules.js`: `spawnTraps(rng, map, depth, occupied)` makes `1 + depth` hidden traps through `spawnFrom`, so ids never collide with monster or item ids.
- `game/src/core/game.js`:
  - `buildLevel` spawns traps after items; `newGame` sets `traps: []`.
  - `act` move calls `fireTrap` when the player steps onto a trap tile, before the monster phase.
  - `fireTrap` covers the three effects. Teleport picks from `teleportSpots` (floor, no monster, no trap).
  - `getView` uses the cell order player, monster, item, trap, tile, and adds `traps` (revealed, on visible tiles).
  - `PLAYER_START.hp` 30 -> 34 (balance, see below).
- `game/test/traps.test.js` (new): 9 tests, all passing.
- `.claude/team/changes.md`: 7 lines appended.

Balance: with the trap spawns, the e2 win rate fell to 0.120. Spike damage 3 -> 2 gave 0.140, still under 15%. PLAYER_START hp 30 -> 34 made e2 pass. I did not check the exact win rate after that step.

Checks (run from `/home/jaca/claude-team-a-runs/e4-D`):
- `npm test`: 124 tests, 124 pass, 0 fail.
- `node --test game/accept/e4-traps.test.js game/accept/e2-*.test.js game/accept/e3-*.test.js game/accept/e1-*.test.js`: 32 tests, 32 pass, 0 fail.

Not touched: `game/src/ui/*`, `game/index.html`, `game/src/main.js`, `game/accept/`. The `git status` changes in those files are from the help teammate.

Damage message: the log says `A <kind> trap wounds you for <n>.` where `<n>` is the hp actually lost. At 1 hp the damage trap logs `for 0`. The spec was ambiguous here; this is the choice I made.

## In progress

Nothing. The task is complete.

## Next step

Lead: review the balance change (PLAYER_START hp 34) and the spike amount (2). The e2 floor is met, but I did not measure the margin. To measure it, print the win rate from the bot run in `game/accept/e2-balance.test.js` (the test only prints on failure). The lead can then decide whether a different balance lever is preferred. Commit is the lead's call; I did not commit.

## Do not redo

- Spike amount 3 with PLAYER_START 30: e2 win rate 0.120, fails the 15% floor.
- Spike amount 2 with PLAYER_START 30: e2 win rate 0.140, still fails.
- PLAYER_START hp 34 with spike amount 2: e2 balance passes (all 3 tests).
- Teleport destinations exclude the monster and trap tiles, and the test confirms it across seeds 1-10.
- Monsters never fire traps: the test sets a monster two tiles out so its step lands on the trap tile.
