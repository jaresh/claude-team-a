# Handoff: help

## Done

Help overlay per "e4: help overlay" in `game/ARCHITECTURE.md`.

Files changed (not committed):
- `game/src/ui/help.js` (new): `HELP_KEYS` (7 rows: move, wait, pick up, descend, use item, help, close help) and `glyphRows(view)` (you, stairs, then one row per trap kind in first-seen order; tolerates a view with no `traps` field).
- `game/src/ui/input.js`: `?` -> `{type:'help'}`, `Escape` -> `{type:'close'}`, `buttonToAction` `help` -> `{type:'help'}`.
- `game/src/main.js`: `help` toggles `#help` panel's `hidden`; `close` hides it. Neither is passed to `act`.
- `game/index.html`: `?` button (`data-action="help"`) in the actions group; `<ul id="help" hidden>` after `#legend`; CSS for `#help`; hint text mentions `? help, Esc close`.
- `game/src/ui/render.js`: `renderHelp()` fills `#help` each draw: one line per `HELP_KEYS` entry, then one per `glyphRows(view)` row in that row's colour.
- `game/src/ui/mock-game.js`: one spike trap at (6,4) in state (`enterLevel`, `newGame`); `getView` returns `traps` filtered to visible cells, shape `{kind, glyph, color, x, y}`.
- `game/test/help.test.js` (new): 7 tests covering HELP_KEYS, glyphRows, input mapping, and the mock traps field.

Check results:
- `node --test game/test/help.test.js game/test/ui.test.js game/test/hud.test.js game/test/legend.test.js game/accept/e4-help.test.js`: 31 tests, 31 pass, 0 fail.
- `node --check` passes for `game/src/main.js`, `game/src/ui/help.js`, `game/src/ui/input.js`, `game/src/ui/render.js`, `game/src/ui/mock-game.js`.
- Browser check not run (no browser here; lead runs it).

Design notes:
- The help panel does not pause the game. Turns still run while it is open; the spec does not say to pause.
- No DOM at import time in help.js; DOM only inside render/bindInput/main's bind callback.
- `main.js` still imports `./core/game.js` (unchanged). The traps teammate's `getView` must return `traps` for the real game, or `glyphRows` falls back to the two base rows (no crash).

## In progress

Nothing. Task complete.

## Next step

Lead: run the browser check (`python3 -m http.server` from `game/` or the usual launcher), press `?` and tap the `?` button to confirm the panel toggles, press Esc to confirm it closes. Then, once traps lands in core, confirm trap rows appear in the panel after a trap is revealed.

## Do not redo

- Did not touch `game/src/core/`, `game/src/data/`, or `game/accept/`.
- Did not commit.
- Checked that `glyphRows` dedupes by kind (the accept test has two spikes and expects one spike row).
