# Plan e4
Goal: add traps and help overlay per game/ARCHITECTURE.md sections "e4: traps" and "e4: help overlay" (read only your section + Conventions).
Check: npm test && node --test "game/accept/*.test.js"  (browser smoke is the lead's).
Contract: View gains `traps: [{kind,glyph,color,x,y}]` (visible, non-hidden only); help.js `glyphRows(view)` reads view.traps. Trap kinds in TRAPS: spike(damage,'^','#c9d1d9'), plus at least a poison and a teleport kind with distinct colours. Actions `help`/`close` handled in main.js only.
Rules: do not edit game/accept/ or game/sim/ or ARCHITECTURE.md. Do not commit. Log edits to shared files in .claude/team/changes.md. Add your own test file in game/test/ (one per new module: traps.test.js / help.test.js); keep existing tests passing. Acceptance tests game/accept/e4-traps.test.js and e4-help.test.js are your spec; read yours.

## traps
Owns: game/src/data/traps.js (new), game/src/core/rules.js, game/src/core/game.js, game/test/traps.test.js (new), and existing game/test/ files if a change requires it. May tune TRAPS `amount` values if game/accept/e2-balance.test.js needs it (log it in changes.md).
Done: `npm test && node --test game/accept/e4-traps.test.js game/accept/e2-balance.test.js`
Must not touch: game/src/ui/, index.html, main.js.

## help
Owns: game/src/ui/help.js (new), input.js, render.js, mock-game.js, game/src/main.js, game/index.html, game/test/help.test.js (new), game/test/ui.test.js.
Done: `npm test && node --test game/accept/e4-help.test.js`
Must not touch: game/src/core/, game/src/data/. The panel must have id="help", hidden at start; a `?` button with data-action="help".
