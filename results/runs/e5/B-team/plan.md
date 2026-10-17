# Plan e5
Goal: add features "e5: score and stats" and "e5: run summary and high scores" per game/ARCHITECTURE.md (read those two sections + Conventions).
Check: `npm test && node --test "game/accept/*.test.js" && node game/tools/smoke.mjs out/e5/B.png --ids inventory,hpbar,end,legend,help,scores` (lead runs it; smoke is the lead's).
Contract: view gets `stats` (deep copy) and `score`; exactly as in ARCHITECTURE.md. UI uses view.stats, view.score, view.hud.turn only. Never edit game/accept/, game/sim/, game/tools/, ARCHITECTURE.md.

## score
Owns: game/src/core/score.js (new), game/src/core/game.js, game/test/score.test.js (new; unit tests for score formula and stats counting). May change game.js freely for stats (kills, itemsUsed, trapsTriggered, deepest, damageTaken incl. melee, shots, traps, poison) and getView. Keep e2 balance unchanged. Done check: `npm test && node --test game/accept/e5-score.test.js`. Must not touch game/src/ui/, game/src/main.js, other tests' expectations.

## summary
Owns: game/src/ui/scores.js (new), game/index.html, game/src/ui/render.js, game/src/main.js, game/src/ui/mock-game.js, game/test/scores.test.js (new). May change those files freely to meet the contract: `#scores` list inside `#end`, summary rows and high scores shown in #end when game ended, main.js adds each finished game once and saves with try/catch, mock view has stats and score. Keep existing UI tests passing. Done check: `npm test && node --test game/accept/e5-scores.test.js`. Must not touch game/src/core/, game/src/data/.
