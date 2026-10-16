# Handoff: rules (M0 wave 1)

## Done
- `game/src/data/monsters.js`: 6 kinds (rat d1, kobold d2, goblin d2, bat d3, orc d4, troll d5).
- `game/src/data/items.js`: 4 kinds (potion heal 8 d1, whetstone atk 1 d1, ring def 1 d2, great potion heal 16 d4).
- `game/src/core/rules.js`: spawnMonsters, spawnItems, attack, applyItem, monsterStep per ARCHITECTURE.md.
  - Imports only `data/monsters.js` and `data/items.js`. FLOOR '.' and STAIRS '>' are repeated locally (no import of core/map.js).
  - Entity/Item ids = tile index + 1 (unique per level, since monsters and items share `occupied`).
  - Spawns stop early if no free floor tile is left (returns fewer than requested, no throw).
  - `attack` mutates `defender.hp` only. `applyItem` mutates `player` only. `monsterStep` mutates nothing.
  - `monsterStep` visible branch: attack if Chebyshev distance is 1; else move to the walkable, unblocked neighbour with the lowest Chebyshev distance to the player (ties broken by squared Euclidean); wait if none. Not visible: random walkable unblocked neighbour via rng.pick, or wait.
- `game/test/rules.test.js`: 18 tests, all pass (`node --test game/test/rules.test.js`).
- Files changed: the four owned files only. `results/changes.md` not touched (new files, no shared generator edited).

## In progress
- Nothing. Task complete.

## Next step
- None for this teammate. Lead: run `node --test game/test/rules.test.js` once more after merge, and check that game/src/core/game.js calls `monsterStep(map, monster, player, visible, isBlocked, rng)` with `visible` as a Set of tile indices.

## Do not redo
- Test fake rng: `seqRng(vals)` in the test file, int(min,max) = min + (v % span). Reuse it, do not rewrite.
- Map rows in the spawn test must all be the same width (an earlier draft had 10/11-wide rows; fixed).
- No changes to rng.js, map.js, fov.js or ui/ (not owned, not touched).
