# Plan
Goal: add traps and help overlay per game/ARCHITECTURE.md sections "e4: traps" and "e4: help overlay" (read them; they are the Contract).
Check: npm test && node --test "game/accept/*.test.js" && node game/tools/smoke.mjs out/e4/B.png --ids inventory,hpbar,end,legend,help (lead runs it; do NOT run smoke.mjs).
Contract: ARCHITECTURE.md sections above. View.traps = [{kind,glyph,color,x,y}] (not hidden, visible tiles). Teammates never commit; do not edit game/accept/ or game/sim/.

## traps
Owns: game/src/data/traps.js (new), game/src/core/rules.js, game/src/core/game.js, game/test/ (add traps tests, e.g. game/test/traps.test.js).
Implement the "e4: traps" section. Done check: `npm test && node --test game/accept/e4-traps.test.js` (acceptance test shows the expected behavior; also keep e2-balance acceptance passing). Must not touch game/src/ui/, main.js, index.html. Log shared-file edits (traps.js amounts) in .claude/team/changes.md.

## help
Owns: game/src/ui/help.js (new), input.js, render.js, mock-game.js, game/src/main.js, game/index.html, game/test/ (add help tests, e.g. game/test/help.test.js).
Implement the "e4: help overlay" section. Done check: `npm test && node --test game/accept/e4-help.test.js`. Must not touch game/src/core/, game/src/data/.
