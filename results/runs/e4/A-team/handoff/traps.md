# Handoff: traps (e4)

## Done

- `game/src/data/traps.js` (new): `TRAPS` with three rows: `spike` (damage, amount 2, minDepth 1),
  `poison needle` (poison, minDepth 2), `teleport` (teleport, minDepth 2). Glyphs `^`, `*`, `~`.
- `game/src/core/rules.js`: `spawnTraps(rng, map, depth, occupied)` (1 + depth hidden traps, via the
  shared `spawnFrom`, so ids never collide with monster or item ids). Imports `TRAPS`.
- `game/src/core/game.js`:
  - `traps: []` in the new state; `buildLevel` spawns traps after items with the same `occupied`.
  - `triggerTrap` runs on a player move onto a walkable tile, before the monster phase. Damage
    (never below 1, logs the actual loss), poison (`POISON_TURNS`), teleport (`teleportTarget`:
    random FLOOR tile with no monster and no trap, using the game rng).
  - `getView`: trap cells after items and before tiles, only for revealed traps on visible tiles;
    `traps: [{ kind, glyph, color, x, y }]`.
  - `PLAYER_START.hp` 30 -> 32 (balance, see below).
- `game/test/traps.test.js` (new): 10 tests covering spawning, each effect, monsters never
  triggering, view reveal, and descend.
- `.claude/team/changes.md`: five lines logged (table creation, spawnTraps, game.js, spike amount,
  PLAYER_START).
- Done check: `node --test game/test/traps.test.js game/test/rules.test.js game/test/game.test.js
  game/test/abilities.test.js game/accept/e4-traps.test.js game/accept/e2-balance.test.js`:
  64 pass, 0 fail.

Balance on `game/sim/seeds-200.txt` (`.claude/team/scratch/traps/stats.mjs`):

| Setup | Win rate | Mean depth | Result |
|---|---|---|---|
| Baseline (no traps) | 0.210 | 4.08 | pass |
| Traps, spike 3, hp 30 | 0.135 | 3.87 | win rate fails |
| Traps, spike 2, hp 30 | 0.150 | 3.90 | passes on the boundary (30/200) |
| Traps, spike 2, hp 32 (current) | 0.165 | 4.00 | pass |

No monster kind exceeds 40% of deaths (largest: goblin 45 of 167, about 27%).

## In progress

Nothing. The task is complete.

## Next step

The lead commits (I did not). Optional: `npm test` for the full suite, and `node --test
game/test/traps.test.js` to rerun the new tests alone. The worktree also holds the `help`
teammate's uncommitted edits (index.html, main.js, input.js, mock-game.js, render.js); they are not
mine and I did not touch them.

## Do not redo

- EnterWorktree is not in my tool set, and the cwd `/home/jaca/claude-team-a-runs/e4-A` is already a
  git worktree of this repo, so I edited in place. Nothing needs isolating.
- Changing spike to 3 with hp 30 fails the win rate (0.135). Do not retry it.
- `game/sim/bot.mjs` and `game/accept/` were not edited. The bot does not know about traps, so it
  walks onto hidden traps; that is intended.
- Not changed, and out of my scope: `endTurn` runs the monster phase before the death check, so a
  monster can still attack after a trap or poison drops the player to 0. Traps alone cannot kill
  (damage floors at 1), so this only matters for poison, and it is pre-existing e3 behaviour.
- `game/ARCHITECTURE.md` was not edited (not my file).
