# Plan e5

**Goal**: add score/stats (core) and run summary/high scores (UI) per `game/ARCHITECTURE.md`
sections "e5: score and stats" and "e5: run summary and high scores". Read your section there.
**Check**: `npm test && node --test "game/accept/*.test.js"` (browser smoke check is the lead's).
Never edit `game/accept/`, `game/sim/`, `game/ARCHITECTURE.md`, or other tasks' files. Log each edit
to a shared file in `.claude/team/changes.md`.

## Contract
View gets `stats: {kills:{kind:n}, itemsUsed, trapsTriggered, deepest, damageTaken}` and `score` (int),
exactly as in ARCHITECTURE. UI task relies only on `view.stats`, `view.score`, `view.hud.turn`,
`view.hud.depth`, `view.status`, `view.seed` (check getView/mock-game for the seed field name; if getView has no seed, main.js keeps the seed it passed to newGame).

## score
Owns: `game/src/core/score.js` (new), `game/src/core/game.js`, `game/test/score.test.js` (new, unit tests; may also extend `game/test/game.test.js`).
Do: implement `score()`, `stats` in GameState/newGame, all counters (kills, itemsUsed, trapsTriggered, deepest, damageTaken incl. melee, shots, traps, poison), `getView` stats deep copy + score. May change anything in those files needed; must not change balance/behaviour.
Done check: `npm test && node --test game/accept/e5-score.test.js`
Must not touch: `game/src/ui/*`, `game/src/main.js`, `index.html`.

## summary
Owns: `game/src/ui/scores.js` (new), `game/src/ui/render.js`, `game/src/ui/mock-game.js`, `game/src/main.js`, `game/index.html`, `game/test/scores.test.js` (new).
Do: implement scores.js, `#scores` list inside `#end`, render summary rows + high scores when ended, main.js adds each finished game once and saves (try/catch storage), mock-game returns `stats` and `score`. May change anything in those files (incl. styles) needed. Keep existing tests passing.
Done check: `npm test && node --test game/accept/e5-scores.test.js`
Must not touch: `game/src/core/*`, `game/accept/`.
