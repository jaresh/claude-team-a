# Plan
Goal: add e4 traps and e4 help overlay per game/ARCHITECTURE.md sections "e4: traps" and "e4: help overlay" (read only your section + Conventions). Tests: node:test, one file per module in game/test/. Never edit game/accept/, game/sim/, game/tools/ (lead's). Log each edit to a shared file in .claude/team/changes.md (one line). Do not commit.
Check: npm test && node --test "game/accept/*.test.js" && node game/tools/smoke.mjs out/e4/D.png --ids inventory,hpbar,end,legend,help
Contract: Trap = { id, kind, glyph, color, effect, amount, x, y, hidden }. View.traps = [{kind, glyph, color, x, y}] (visible, non-hidden). The two tasks are independent: help uses view.traps only via mock-game.js.

## traps
Owns: game/src/data/traps.js (new), game/src/core/rules.js, game/src/core/game.js, game/test/traps.test.js (new; add tests), existing game/test/*.test.js if they need updating.
Do: implement the "e4: traps" section fully. Read game/accept/e4-traps.test.js (read-only) to see what is checked. May change for the e2 balance targets: everything the e2 balance and e4 traps Balance bullets allow (TRAPS amounts, monsters/items rows, spawn counts, PLAYER_START, level-up gains).
Done check: npm test && node --test "game/accept/e4-traps.test.js" "game/accept/e2-*.test.js" "game/accept/e3-*.test.js" "game/accept/e1-*.test.js"
Must not touch: game/src/ui/*, game/index.html, game/src/main.js.

## help
Owns: game/src/ui/help.js (new), game/src/ui/input.js, game/src/ui/render.js, game/src/ui/mock-game.js, game/src/main.js, game/index.html, game/test/help.test.js (new).
Do: implement the "e4: help overlay" section fully. Read game/accept/e4-help.test.js (read-only). The #help panel must be hidden at start, toggled by main.js. Keep existing ids (inventory, hpbar, end, legend) working.
Done check: npm test && node --test game/accept/e4-help.test.js game/accept/e1-camera.test.js game/accept/e2-hud.test.js game/accept/e3-legend.test.js
Must not touch: game/src/core/*, game/src/data/*.
