# Handoff: abilities (run e3)

## Done
- `game/src/data/monsters.js`: `ability` on every row. bat `poison`, orc `ranged`, troll `regen`,
  goblin and the rest `null`. New row appended: `spider` (minDepth 3, ability `poison`). 7 kinds.
- `game/src/core/rules.js`: `spawnMonsters` copies `ability`. `monsterStep` returns `{ type: 'shoot' }`
  for a ranged monster at Chebyshev 2 to 4 on a visible tile (after the adjacent-attack check).
- `game/src/core/game.js`: `POISON_TURNS = 3`; `player.poison` starts at 0; `monsterPhase` handles
  `shoot` (atk - 1, min 1, logs `shoots you for N`) and sets poison on melee hits from poison
  monsters; `regenerate` runs after `monsterPhase`; `endTurn` applies poison (-1 hp, -1 turn,
  logs `Poison hurts you.`) before the death check; `getView` adds `hud.poison` and
  `visibleMonsters`.
- `game/test/abilities.test.js`: 4 tests (shot damage range and log, poison on melee, no poison on
  plain melee, poison death).
- `results/changes.md`: 6 rows appended (abilities).
- Tests: `node --test game/test/abilities.test.js game/test/rules.test.js game/test/game.test.js
  game/accept/e3-abilities.test.js game/accept/e2-balance.test.js`: 48 pass, 0 fail.
- Balance on `game/sim/seeds-200.txt` (via `scratch/abilities/stats.mjs`): won 31 of 200
  (15.5%), mean depth 4.17, deaths 169: goblin 35 (20.7%, worst), bat 28, orc 27, troll 24,
  kobold 22, spider 17, rat 16. All e2 targets hold.
- No e2 tuning constants changed (spawn counts, PLAYER_START, level-up gains untouched).

## In progress
- Nothing. Work complete; the handoff is the last step.

## Next step
- Lead: merge check. Read `results/changes.md` (abilities rows) and this file, then run
  `node --test game/test/abilities.test.js game/test/rules.test.js game/test/game.test.js game/accept/e3-abilities.test.js game/accept/e2-balance.test.js`.
- Lead should watch the balance margin: win rate 15.5% is close to the 15% floor. Any further
  change to `legend` or `ui` that affects the bot's view is not expected to change the sim, but
  re-run the e2 balance test after merge.

## Do not redo
- Regen on goblin: tried, win rate fell to 9.0%, goblin was 40% of deaths. Regen now only on
  troll (depth 5). Do not put it back on goblin without re-tuning.
- No edits to `game/sim/`, `game/accept/`, `game/src/ui/`, `game/index.html`. Not touched.
- Balance was not tuned with spawn counts or PLAYER_START; the ability assignment alone brought
  the win rate back into range.
