# Handoff: game (M0 wave 2: core/game.js)

## Done
- `game/src/core/game.js`: exports `MAX_DEPTH = 5`, `FOV_RADIUS = 8`, `newGame(seed)`, `act(state, action)`,
  `getView(state)` per the ARCHITECTURE.md section. Imports rng, map, fov and rules only.
- `game/test/game.test.js`: 16 tests, all pass (`node --test game/test/game.test.js`).
- `game/src/main.js`: line 1 switched to `import { newGame, act, getView } from './core/game.js';`. Nothing else changed.
- Check: `node --test game/test/game.test.js game/test/ui.test.js` -> 27 pass, 0 fail.
- Files touched: the three owned files only. `results/changes.md` not touched (no shared generator edited).

## Decisions the architecture does not spell out (lead may review)
- Player: id 0, glyph '@', hp 20, atk 2, def 0. Level-up gives +5 maxHp and +1 atk only (no hp heal).
- xp is the running total; `level = 1 + floor(xp / 10)`; each crossed multiple of 10 gives one level-up.
- Monsters act using `state.visible` from the last FOV update (the order in the architecture: monsters, then FOV).
- `descend` does not run the monster phase; it still increments `turn`. Descend on MAX_DEPTH sets 'won' and increments `turn`.
- Moving into a wall logs 'A wall blocks the way.' and costs no turn. Pickup on an empty tile, use of an
  invalid index and `move` with dx/dy outside -1..1 (or 0,0) are no-ops.
- String seeds (from `?seed=`) are hashed with FNV-1a to a uint32; `state.seed` keeps the original value.
- `state.log` is capped at 50 lines; `getView` returns the last 5.
- Explored-but-not-visible tiles are drawn in dim colour `#2a303b`, unexplored as `' '` with the same colour.

## In progress
- Nothing. Task complete.

## Next step
- Lead: after merge run `node --test game/test/game.test.js game/test/ui.test.js` and `npm test`.
- Lead, manual: `npm run serve`, open http://localhost:8000/game/?seed=42 and check a real game (not done here, no browser).
- Optional: `game/src/ui/mock-game.js` is no longer used by main.js; ui.test.js still imports it, so keep it until the UI test is repointed (ui owner's file, not touched here).

## Do not redo
- The 200-turn random walk (5 seeds) runs in about 170 ms; no need to tune it.
- The wall-bump test picks a floor tile next to a wall by scanning the map, so it does not depend on the seed.
- Monster-kill test sets `state.monsters` explicitly; spawned monsters are cleared in tests to keep them deterministic.
