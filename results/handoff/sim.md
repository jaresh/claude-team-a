# Handoff: sim (wave 3: sim/bot.mjs)

## Done
- `game/sim/bot.mjs`: exports `chooseAction(state)` and `playGame(seed, maxTurns = 5000)`. CLI
  (guarded by an `import.meta.url` check) runs `--seeds <file> --out <file>` and writes
  `{ seeds: [...], summary: {...} }`. Policy order: attack adjacent monster (lowest hp first); heal if
  hp < 40% and a `heal` item is held; pick up item underfoot; descend on stairs, or BFS to explored
  stairs; BFS to nearest explored walkable frontier tile; else wait.
- `game/sim/seeds-sample.txt`: 5 seeds (42, 7, 1234, 99, 2026).
- `game/test/bot.test.js`: 3 tests, all pass (`node --test game/test/bot.test.js`).
- Sample run: `node game/sim/bot.mjs --seeds game/sim/seeds-sample.txt --out scratch/sim/sample.json`
  wrote `scratch/sim/sample.json`. Summary: 5 games, winRate 0, meanDepth 2.8, meanTurns 188.4,
  deathsByKind {kobold: 3, bat: 1, goblin: 1}. All 5 died; none reached maxTurns.
- Files touched: the three owned files plus `scratch/sim/sample.json`. No shared file edited, so
  `results/changes.md` is not touched.

## Decisions
- `killedBy` is not exposed by game.js. It is taken from the log: the last `The <kind> hits you for N.`
  line. The killing blow is always the last monster hit (the player cannot be hit after death), so this
  is exact for these logs. `killedBy` is null for won and maxTurns games.
- `status` values: `dead`, `won`, or `maxTurns` (the game still `playing` at the cap).
- `playGame` has a guard of `maxTurns * 4` actions, so a no-turn action loop cannot hang.
- `chooseAction` never returns a no-op: pickup only when an item is underfoot, use only with a valid index.
- Seeds file: numeric lines become numbers, other lines stay strings. Blank and `#` lines are skipped.
- `winRate` and `meanDepth` are not rounded in the JSON.

## In progress
- Nothing. Task complete.

## Next step
- Lead: run the full job when ready: `node game/sim/bot.mjs --seeds game/sim/seeds-200.txt --out <new empty folder>/seeds-200.json`
  (use a new folder per rule 12, e.g. `scratch/sim/run-200/`). The sample is correct; no changes needed first.
- Lead: `node --test game/test/bot.test.js` to recheck the tests after the merge.
- Finding for the lead: the greedy bot wins 0 of 5 sample games and dies at depths 2-3. A win rate
  signal needs a stronger policy (for example, fleeing at low hp or drinking potions earlier). That is a
  design call and was not done here.

## Do not redo
- Checked that the 3 tests pass and the sample writes valid JSON with all 5 seeds.
- Checked the policy by reading `game.js` and `rules.js`: monsters attack only when adjacent or in view,
  and moving into a monster attacks it, so a path through a monster is safe to take. No corner-cutting
  rule exists, so BFS uses all 8 directions.
- Do not add a stall guard for the case "standing on the only frontier tile" without evidence. In the
  sample no run reached maxTurns, so it did not occur there.
