# Handoff: score

## Done

- `game/src/core/score.js` (new): `score(stats, status)` per ARCHITECTURE "e5: score and stats".
  Integer, floored at 0.
- `game/src/core/game.js`:
  - imports `score`.
  - `newGame` sets `stats: { kills: {}, itemsUsed: 0, trapsTriggered: 0, deepest: 1, damageTaken: 0 }`.
  - `playerAttacks`: kill counted by `target.kind`.
  - `use` action: `itemsUsed += 1` once the item is spliced out.
  - `triggerTrap`: `trapsTriggered += 1` each time a trap is found under the player; damage traps add their real hp loss to `damageTaken`.
  - `monsterPhase`: melee and shoot add the real hp drop (`before - p.hp`) to `damageTaken`.
  - `ticksPoison`: `damageTaken += 1`.
  - `descend`: `deepest = max(deepest, depth)`.
  - `getView`: `stats` is a copy (`kills` copied too), and `score: score(state.stats, state.status)`.
- `game/test/score.test.js` (new): 4 unit tests for the formula (depth, kills, items, traps, won bonus, 0 floor, damage not scored).
- Balance and RNG use are unchanged: no new rng calls, and no change to any hp, drop or spawn value.

Checks:
- `npm test`: 132 tests, 132 pass, 0 fail.
- `node --test game/accept/e5-score.test.js`: 6 tests, 6 pass, 0 fail.

No edits to shared files, so `changes.md` is untouched. Nothing committed.

## In progress

Nothing. The task is complete.

## Next step

None for this task. The lead runs the browser smoke check. The summary teammate needs `view.stats`, `view.score`, `view.hud.turn` and `view.hud.depth`, which are now in `getView`.

Note for the summary task: `getView` has no `seed` field. The contract's fallback applies: `main.js` keeps the seed it passed to `newGame`. I did not add one, because it is not in the ARCHITECTURE spec.

## Do not redo

- Checked that every hp loss for the player goes through one of three sites: `ticksPoison` (game.js), `triggerTrap` (game.js) or `attack()` in rules.js (`defender.hp -= damage`). `applyItem` only heals. So the three counters cover all damage.
- Checked that `getView` has no existing deepEqual test in `game/test/` that the new `stats`/`score` fields would break. All 132 tests pass.
- The first run of my unit test failed because my test case was wrong (10 traps with deepest 1 gives 80, not 0). I fixed the test to use 100 traps. The formula was not changed.
