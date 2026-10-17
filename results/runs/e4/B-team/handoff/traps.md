# Handoff: traps

## Done
- `game/src/data/traps.js` (new): TRAPS with spike (damage, amount 2, minDepth 1), poison needle (poison, amount 3, minDepth 2), teleport (teleport, amount 0, minDepth 3).
- `game/src/core/rules.js`: `spawnTraps(rng, map, depth, occupied)` via `spawnFrom`, `1 + depth` hidden traps. Ids are tile-index based, so they cannot collide with monster or item ids.
- `game/src/core/game.js`: `state.traps` (set in `newGame` and `buildLevel`, spawned after items with the same `occupied`); `triggerTrap` runs on a player move, before the monster phase; `getView` adds the trap cell (after item, before tile, visible and not hidden only) and `View.traps`.
- `game/test/traps.test.js` (new): 5 tests (id collisions, monsters do not trigger traps, teleport target, damage floor and log, view filtering). All pass.
- `.claude/team/changes.md`: 4 lines logged.
- Checks: `npm test` 121/121 pass. `node --test game/accept/e4-traps.test.js` 7/7 pass.
- **Check NOT green:** `node --test game/accept/e2-balance.test.js` fails: `win rate 0.140` (floor 0.15). HEAD baseline is 0.210 (measured with the same bot and seeds).

## In progress
- Stopped at the e2 balance conflict. The contract and the acceptance test fix poison at 3; with poison 3, no spike amount I tried passes e2.

## Measured e2 win rate (game/sim/seeds-200.txt, bot playGame 5000)
| spike amount | poison amount | win rate | mean depth |
|---|---|---|---|
| 3 | 3 | 0.120 | - |
| 2 | 3 | 0.140 | 3.90 |
| 1 | 3 | 0.140 | 3.95 |
| 1 | 1 | 0.150 | 3.99 |
| 2 | 1 | 0.150 | 3.92 |
| 3 | 1 | 0.135 | 3.91 |
| 2 | 2 | 0.135 | - |
| 1 | 2 | 0.140 | - |
| 1 | 0 (poison off) | passes the 0.15 floor (exact rate not measured) | - |

- Poison is the main cost. Teleport off also did not fix it (with poison 3 it was 0.145).
- The acceptance test `a poison trap poisons the player` requires `poison` in [2, 3] after one move (set to amount, then one same-turn tick). That allows amount 3 only. Amount 1 or 2 fails it.
- So the spec as written (poison = 3, same-turn tick, e2 floor 0.15) cannot all pass with these traps. Current files: spike 2, poison 3 (acceptance passes, e2 gives 0.140).

## Next step
Lead decision needed, one of:
1. Accept the e2 change: the lead updates `game/accept/e2-balance.test.js` or the bot-relevant target, or lets e2 stay failing for this run. Then nothing else changes.
2. Change the trap design in `ARCHITECTURE.md` "e4: traps" (for example, the poison trap does not tick on the turn it fires, or fewer traps at shallow depth). That needs a contract change, which is not mine to make.
3. Lower trap damage further (spike 1, poison 1): passes e2 at 0.150 but fails the acceptance test (`a poison trap poisons the player`).
After the decision, re-run: `npm test && node --test game/accept/e4-traps.test.js && node --test game/accept/e2-balance.test.js`. Rates script: `node .claude/team/scratch/traps/rates.mjs` (prints win and depth for the current amounts, about 1 minute).

## Do not redo
- Baseline before my change: `npm test` 111/111 and e2 3/3 pass on HEAD.
- Spike amount 3 with poison 3 gives 0.120; spike 2 or 1 with poison 3 gives 0.140. Do not retry these.
- Poison 1 or 2 fails `a poison trap poisons the player`, so do not lower poison below 3 unless the acceptance test or contract is changed.
- Not touched: `game/accept/`, `game/sim/`, `game/src/ui/`, `main.js`, `index.html`. Nothing committed.
