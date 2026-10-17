# Handoff: help overlay

## Done
- `game/src/ui/help.js` (new): `HELP_KEYS` (7 rows: move, wait, pick up, descend, use item, help, close help) and `glyphRows(view)` (you, stairs, then one row per trap kind, first-seen order).
- `game/src/ui/input.js`: `?` -> `{type:'help'}`, `Escape` -> `{type:'close'}`; `buttonToAction` maps `data-action="help"` and `data-action="close"`. The close case is an addition beyond the contract, so touch users can close the panel without Esc.
- `game/src/ui/render.js`: `renderHelp` fills `#help .help-lines` with one `li` per `HELP_KEYS` row and one per `glyphRows(view)` row, in that row's colour.
- `game/src/main.js`: `help` toggles `#help` hidden; `close` hides it. Both are handled before `act`, so they never reach the game. Other actions still work while the panel is open (not modal).
- `game/index.html`: `?` button (`data-action="help"`) in the actions group; `<section id="help" hidden>` with a `.help-lines` list and a Close button (`data-action="close"`) after `#legend`; CSS for it, including a `[hidden]` rule; hint text now mentions `? help`.
- `game/src/ui/mock-game.js`: two fixed traps (spike, teleport) per level in `state.traps`; drawn as `^` on seen tiles; `getView` returns `traps` filtered to visible tiles.
- `game/test/help.test.js` (new): 5 tests covering HELP_KEYS, glyphRows (no traps, first-seen dedupe), mock view traps, and key/button mapping.

Checks:
- `npm test`: 116 pass, 0 fail.
- `node --test game/accept/e4-help.test.js`: 3 pass, 0 fail.
- `node --check` passes on main.js, render.js, input.js, mock-game.js, help.js.
- Not run: `game/tools/smoke.mjs` (lead's job, per the plan). Panel layout is not visually checked.

No shared-file edits (no data tables), so `.claude/team/changes.md` is untouched. I did not edit `game/src/core/`, `game/src/data/`, or `game/accept/`. The modified `game/src/core/game.js`, `game/src/core/rules.js`, and new `game/src/data/traps.js` in `git status` belong to the traps teammate.

## In progress
Nothing. The task is complete.

## Next step
Lead: run `node game/tools/smoke.mjs out/e4/B.png --ids inventory,hpbar,end,legend,help` and check that the `help` id exists in the page. If smoke.mjs looks for a different id or selector, the `#help` section in `game/index.html` is the element to match.

## Do not redo
- Checked `ARCHITECTURE.md` "e4: help overlay" and "UI" sections; the contract is implemented as written, plus the Close button and `close` button mapping noted above.
- `npm test` already includes the traps teammate's in-progress changes; the 116 passing tests include them.
- The render path needs a DOM, so only the pure helpers are unit-tested. Do not add DOM tests here.
