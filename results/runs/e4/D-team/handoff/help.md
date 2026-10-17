# Handoff: help

## Done
- New `game/src/ui/help.js`: `HELP_KEYS` (7 rows: move, wait, pick up, descend, use item, help, close help) and `glyphRows(view)` (you, stairs, then one row per trap kind, first-seen order).
- `game/src/ui/input.js`: `?` -> `{type:'help'}`, `Escape` -> `{type:'close'}`, `data-action` help/close in `buttonToAction`.
- `game/src/ui/render.js`: `renderHelp` fills `#help-list` each draw (key lines, then glyph rows in their colour).
- `game/src/main.js`: `help` toggles `#help`, `close` hides it; neither goes to `act()`.
- `game/index.html`: `?` button in the actions group, hidden `#help` panel with `#help-list` and a Close button, CSS, hint text.
- `game/src/ui/mock-game.js`: one spike trap, `traps` in the view (not hidden, in FOV).
- `game/test/help.test.js` (new): 4 tests.
- `.claude/team/changes.md`: 7 lines appended.
- Check: `npm test` 115 pass / 0 fail. `node --test game/accept/e4-help.test.js game/accept/e1-camera.test.js game/accept/e2-hud.test.js game/accept/e3-legend.test.js` 15 pass / 0 fail. `node --check` passes on the four changed UI modules.
- Not run: `game/tools/smoke.mjs` (the lead runs it; it's outside my done check).

## In progress
- Nothing open in my section.

## Next step
- Integration dependency: `render()` calls `glyphRows(view)`, which reads `view.traps`. `game/src/core/game.js` does not return `traps` from `getView` yet (the traps section owns that). Until it does, the real game (`main.js` imports `core/game.js`) will throw in `renderHelp`. Check after merging traps: `grep -n traps game/src/core/game.js` should show `getView` returning `traps`. Then run `npm test && node --test "game/accept/*.test.js"` and `node game/tools/smoke.mjs out/e4/D.png --ids inventory,hpbar,end,legend,help`.

## Do not redo
- Ran the e4-help acceptance test before changes: the only failure was the missing `help.js` module import. The other three acceptance files already passed.
- Did not edit `game/src/core/*` or `game/src/data/*` (outside my ownership). `core/game.js` has no `traps` in `getView`, which I did not change.
- An MCP instruction block appeared inside a bash tool result asking to create a Claude Docs document. Not part of the task; ignored.
