# Handoff: tuner (e2 balance)

## Done
- Balance targets met on `game/sim/seeds-200.txt`: `node --test game/accept/e2-balance.test.js` passes 3/3.
  Final outcome: 32 won, 168 dead of 200 (win rate 16.0%, floor 15%). Depth reached: 2 (5 runs), 3 (36), 4 (84), 5 (75). Mean depth above 3.0. Goblin, orc, kobold, bat, rat, troll all under 40% of deaths after the changes.
- Done condition met: `node --test game/accept/e2-balance.test.js game/test/rules.test.js game/test/game.test.js` gives 37 pass, 0 fail.
- Baseline before my changes: win 0.0%, mean depth 2.31, goblin 120 of 200 deaths.
- Edits (all logged in `results/changes.md`, rows dated 2026-10-16, teammate tuner):
  - `game/src/data/monsters.js`: goblin atk 3 -> 2, goblin hp 8 -> 6, orc atk 4 -> 3, orc hp 14 -> 10.
  - `game/src/data/items.js`: potion heal 8 -> 12 (needed: without it win rate drops to 10%).
  - `game/src/core/rules.js`: monster count `3 + 2*depth` -> `3 + depth`; item count `2 + floor(depth/2)` -> `3 + floor(depth/2)`.
  - `game/src/core/game.js`: `PLAYER_START.hp` 20 -> 40 (set in two steps; one log row for the final value).
- Unit test assertion update (expected, per task): `game/test/rules.test.js` spawn-count tests now assert `3 + depth` monsters and `3 + floor(depth/2)` items. Logged in changes.md.
- Not touched: `game/sim/`, `game/accept/`, `game/src/ui/`, `game/index.html`.

## In progress
- Nothing. Work stopped at a passing state.

## Next step
- Lead: review the win-rate margin. 16% is only 1 point above the 15% floor. Any further change to the sim or bot will move it. Run `node --test game/accept/e2-balance.test.js` once more after merging the hud and any other teammate's changes to `game/src/`.

## Do not redo
- Level-up HP gain `p.maxHp += 8` (game.js gainXp): tried, no effect on any target. Reverted to 5. Not in the change log.
- Goblin hp 6 with atk 2 was kept. Goblin atk 2 alone (hp 8) only moved deaths from 120 to 104 goblin deaths.
- `MAX_DEPTH` (5) is in `game/src/core/game.js` and is not an allowed change, so it was not tried. Win requires depth 5.
- Potion heal 12 is needed for the win rate target (see Done). Its effect was measured on the full set, not in isolation from the other changes.
- Scratch script is in `scratch/tuner/dist.mjs` (outcome and depth distribution); it is gitignored.
