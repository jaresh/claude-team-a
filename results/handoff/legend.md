# Handoff: legend (e3 monster legend and poison label)

## Done
- `game/src/ui/legend.js` (new): `legendRows(view)` and `poisonLabel(view)` per the e3 legend section.
- `game/test/legend.test.js` (new): 4 tests (rows, empty rows, ability names, poison label).
- `game/index.html`: `<ul id="legend">` after `#log`, with CSS (hidden while empty).
- `game/src/ui/render.js`: imports the legend helpers; appends the poison label to the HUD text;
  `renderLegend` fills `#legend` with one `<li>` per row, coloured by `row.color`.
- `game/src/ui/mock-game.js`: rat gets `ability: null`; `hud.poison: 0`; `visibleMonsters` from
  living monsters on visible tiles.
- Checks: `node --test game/test/legend.test.js game/test/ui.test.js game/test/hud.test.js
  game/accept/e3-legend.test.js` gives 24 pass, 0 fail. `node --check` passes on legend.js,
  render.js and mock-game.js.

## In progress
- Nothing. Browser check not run (no browser for teammates; the lead runs it).

## Next step
- Lead: run the browser check. Confirm the legend lists monsters in sight and the HUD shows
  `Poisoned (n)` once `core/game.js` sets `hud.poison`.

## Do not redo
- The four-file test command above passed; no need to rerun unless a file changes.
- `game/test/ui.test.js` is not edited (not named in the task); its `assertViewShape` does not check
  `visibleMonsters` or `hud.poison`.
- Not edited: `game/src/core/`, `game/src/data/`, `game/accept/`.
