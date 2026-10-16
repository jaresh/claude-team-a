# Handoff: abilities (run e3)

## Done

- `game/src/data/monsters.js`: `ability` on every row (goblin `poison`, orc `regen`, others `null`);
  new row `archer` appended (ranged, hp 5, atk 3, def 0, xp 5, minDepth 3). 7 kinds.
- `game/src/core/rules.js`: `monsterStep` returns `{ type: 'shoot' }` for a visible ranged monster
  at Chebyshev distance 2-4 (attack stays at distance 1). `spawnMonsters` copies `ability`.
  Spawn count changed to `2 + Math.floor(depth / 2)` (balance, see below).
- `game/src/core/game.js`: `shoot` (atk - 1, min 1, log `The <kind> shoots you for <n>.`);
  `regenerate` after the monster phase; `ticksPoison` in `endTurn` (runs on every turn, including
  descend); a poison melee hit sets `player.poison = 3` (`POISON_TURNS`); player starts with
  `poison: 0`; `getView` adds `hud.poison` and `visibleMonsters`.
- `game/test/abilities.test.js`: new, 10 tests.
- `game/test/rules.test.js`: spawn count assertion updated to `2 + floor(depth / 2)` (needed by the
  balance change; logged).
- `results/changes.md`: 8 rows appended.
- Tests: `node --test game/test/abilities.test.js game/test/rules.test.js game/test/game.test.js
  game/accept/e3-abilities.test.js game/accept/e2-balance.test.js`: 54 pass, 0 fail.
- Balance (bot, seeds-200): win rate 29.5%, mean depth 4.45, worst kind orc at 32% of 141 deaths
  (orc 45, goblin 38, troll 27, kobold 15, bat 6, archer 6, rat 4).

## In progress

Nothing. Not committed (teammates never commit). Did not touch `game/src/ui/`, `game/index.html`,
`game/sim/`, `game/accept/`.

## Next step

Lead: run the whole suite once after merging the legend teammate's UI changes:
`node --test game/test/*.test.js game/accept/*.test.js 2>&1 | grep -E "^# (pass|fail)"`.
Legend needs `getView().visibleMonsters` and `hud.poison`, both present now.

## Do not redo

- Balance with the spawn count at `2 + depth` (baseline with ability): win rate 3.5%, goblin
  poison 40% of deaths. Fails.
- Tried `PLAYER_START.hp` 30 -> 40 with spawn `2 + depth`: win 6.0%. Reverted.
- Tried level-up `maxHp` +5 -> +8 on top of that: win 6.5%. Reverted.
- Turned goblin poison off (diagnostic only, restored): win 8.5%, so poison is not the main cause.
- Spawn `1 + depth`: win 13.0%. Too low.
- Spawn `2 + floor(depth/2)` with original hp and level-up: win 29.5%, passes. This is the kept change.
