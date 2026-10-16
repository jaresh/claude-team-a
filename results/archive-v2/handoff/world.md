# Handoff: world (core/rng, core/map, core/fov)

## Done
- `game/src/core/rng.js`: `createRng(seed)` (mulberry32) with `next`, `int(min,max)` (inclusive), `pick`, `state`.
- `game/src/core/map.js`: `WALL`, `FLOOR`, `STAIRS`, `generateMap(rng, opts)`, `inBounds`, `isWalkable`, `isOpaque`.
  Rooms are placed with a 1-tile gap, joined consecutively by L-corridors, start in rooms[0] centre,
  stairs in last room centre. Retries up to 100 times if fewer than 2 rooms fit.
- `game/src/core/fov.js`: `computeFov(map, x, y, radius)` by ray casting (Bresenham line, Euclidean radius).
  Origin is always included; opaque tiles at the end of a line are included.
- Tests: `game/test/rng.test.js` (5), `game/test/map.test.js` (23: border, determinism, 20 seeds x
  room/BFS reachability, helpers), `game/test/fov.test.js` (5).
- Result: `node --test game/test/rng.test.js game/test/map.test.js game/test/fov.test.js` -> 33 pass, 0 fail.
- No shared files edited. No commits.

## In progress
- Nothing. Task complete.

## Next step
- None for this module. If core/rules.js or core/game.js needs changes to these modules, the lead decides.
  Run `node --test game/test/rng.test.js game/test/map.test.js game/test/fov.test.js` to re-check.

## Do not redo
- Ruled out: shadowcasting (not needed; ray casting meets the contract).
- Checked: the 20-seed reachability test passes for seeds 1-20 with default opts (60x30, up to 12 rooms).
- Not checked: non-default opts (small maps, large minRoom). `generateMap` throws if it cannot place two rooms.
