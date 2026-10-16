# Handoff: tuner (e2 balance)

## Done
- `node --test game/accept/e2-balance.test.js` passes: win rate 0.21 (target 15-40%), mean depth 4.39 (target >= 3.0), worst kind troll at 45 of the deaths (under 40% share). Bot run: `scratch/tuner/t15.json`.
- Baseline before any change: win 0.000, mean depth 2.31, goblin 120 of 183 deaths (about 66%).
- `node --test game/accept/e2-balance.test.js game/test/rules.test.js game/test/game.test.js`: 37 of 37 pass.
- Unit-test assertions changed on purpose (game/test/rules.test.js): "spawnMonsters makes 3 + 2*depth" is now "2 + depth"; "spawnItems makes 2 + floor(depth/2)" is now "4 + floor(depth/2)" with the expected table `{1: 4, 2: 5, 3: 5, 4: 6, 5: 6}`.
- Edits, all logged in results/changes.md (rule 13):
  - game/src/core/game.js: PLAYER_START hp 20 -> 30
  - game/src/core/rules.js: monster count 3 + 2*depth -> 2 + depth; item count 2 + floor(depth/2) -> 4 + floor(depth/2)
  - game/src/data/monsters.js: goblin atk 3 -> 1; kobold atk 2 -> 1; orc atk 4 -> 2 and hp 14 -> 8
  - game/src/data/items.js: potion heal 8 -> 12
- Not touched: game/src/ui/, game/index.html, game/sim/, game/accept/.

## In progress
- Nothing. Balance is done and the three test files pass.

## Next step
- Lead: merge check. `node --test game/accept/e2-balance.test.js game/test/rules.test.js game/test/game.test.js` should show 37 pass.
- Note for the lead: the win rate is 0.21 on a 200-seed sample. Earlier steps sat at exactly 0.15, which passes only because the check is `>=`. The current margin is comfortable.

## Do not redo
- Level-up max HP gain +5 -> +8 (game/src/core/game.js gainXp): moved the win rate by under 0.5 points, so it was reverted. Net change: none.
- Troll atk 6 -> 5: no change in win rate. Reverted. Net change: none.
- Goblin atk 3 -> 2 alone: goblin share fell only from 66% to 52%, and win rate stayed 0. The goblin change was kept only after the attack went to 1.
- Potion heal 8 -> 10 -> 12: small gains (0.13 -> 0.145). Kept at 12.
