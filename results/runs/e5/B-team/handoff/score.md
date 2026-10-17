# Handoff: score

## Done
- `game/src/core/score.js` (new): `score(stats, status)` per ARCHITECTURE.md e5 (clamped at 0).
- `game/src/core/game.js`:
  - imports `score`; `newGame` sets `stats: { kills: {}, itemsUsed: 0, trapsTriggered: 0, deepest: 1, damageTaken: 0 }`.
  - `playerAttacks`: counts kills by kind.
  - `monsterPhase`: `damageTaken` for melee and shots.
  - `ticksPoison`: `damageTaken` +1 per poison tick.
  - `triggerTrap`: `trapsTriggered` +1 per fire; `damageTaken` for damage traps (hp difference).
  - `act` `use`: `itemsUsed` +1.
  - `act` `descend`: `deepest = max(deepest, depth)`.
  - `getView`: `stats` (copy, kills copied too) and `score`.
- `game/test/score.test.js` (new): 3 unit tests for the formula.
- No other files touched. e2 balance untouched (no rules/data changes).

Checks:
- `npm test`: 131 pass, 0 fail.
- `node --test game/accept/e5-score.test.js`: 6 pass, 0 fail.
- `node --test "game/accept/*.test.js"`: 41 pass, 1 fail. The failure is `game/accept/e5-scores.test.js`, the `summary` task (`game/src/ui/scores.js` does not exist yet). Not caused by this task.

## In progress
- Nothing. Task complete. Changes are uncommitted in `/home/jaca/claude-team-a-runs/e5-B`.

## Next step
- None for this task. Lead: after `summary` lands, run `npm test && node --test "game/accept/*.test.js"`.

## Do not redo
- Checked `rules.js` `attack()`: it subtracts exactly `damage` from `defender.hp`, so `r.damage` equals the hp loss for monster hits and shots. Trap damage is counted from the hp difference because of the `Math.max(1, ...)` floor.
- Checked existing tests for exact-key assertions on `getView` or state: none break (`npm test` is green).
