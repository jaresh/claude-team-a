# Handoff: help overlay (section `help`)

## Done
- `game/src/ui/help.js` (new): `HELP_KEYS` (7 rows: move, wait, pick up, descend, use item, help, close help) and `glyphRows(view)` (you, stairs, then one row per trap kind in first-seen order, reading `view.traps`).
- `game/src/ui/input.js`: `keyToAction` maps `?` to `{type:'help'}` and `Escape` to `{type:'close'}`; `buttonToAction` maps `help` and `close`.
- `game/index.html`: `?` button (`data-action="help"`) in the actions group; panel `<div id="help" hidden>` with a `<ul>` and a Close button (`data-action="close"`); hint line mentions `?`; CSS for the panel.
- `game/src/ui/render.js`: `renderHelp()` fills `#help`'s `<ul>` with one line per `HELP_KEYS` row, then one per `glyphRows(view)` row in that row's colour. Called from `render()`.
- `game/src/main.js`: `help` toggles `#help.hidden`, `close` hides it. Both are handled before `act()`, so game state is untouched.
- `game/src/ui/mock-game.js`: two traps (spike, teleport) on each level, drawn when visible; `getView` returns `traps` filtered to visible tiles.
- `game/test/help.test.js` (new): HELP_KEYS shape, glyphRows empty/dedup/colour, mock view carries traps. 4 tests.
- `game/test/ui.test.js`: added `?`/`Escape` key cases and `help`/`close` button cases.

Checks:
- `npm test`: 115 tests, 115 pass, 0 fail.
- `node --test game/accept/e4-help.test.js`: 3 tests, 3 pass.
- `node --check` on main.js and render.js: OK.
- Browser smoke not run (the lead's job).

Not touched: game/src/core/, game/src/data/, game/accept/, game/sim/, ARCHITECTURE.md, package.json. No shared-file edits, so changes.md has no new line.

## In progress
Nothing. Task complete.

## Next step
Lead: `npm test && node --test game/accept/e4-help.test.js` once more after merging with traps, then the browser smoke: open `game/index.html` via `npm run serve`, press `?` (help panel shows), press Esc (panel hides), check the glyph rows.
Depends on the traps teammate: `glyphRows` needs `view.traps` from the real `core/game.js` getView. Until that lands, the real game's `render()` will throw on `view.traps` being undefined. The mock is fine.

## Do not redo
- `glyphRows` dedups trap kinds by `kind`, keeping the first trap's glyph and colour. The accept test expects this order: you, stairs, spike, teleport, spike gives 4 rows.
- The help action does not close the panel when a game action (move, etc.) is taken. Only `close`/Esc or pressing `?` again closes it. The spec did not say otherwise; if the lead wants moves to close the panel, that is a one-line change in main.js.
- `HELP_KEYS.action` is a human description ("pick up"), not the action type name.
