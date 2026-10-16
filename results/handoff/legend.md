# Handoff: legend (e3 monster legend and poison label)

## Done
- `game/src/ui/legend.js` (new): `legendRows(view)` gives `{ text, color }` per `visibleMonsters` entry, with ` ${ability}` appended only when ability is truthy. `poisonLabel(view)` gives `Poisoned (n)` when `hud.poison > 0`, else null. No DOM.
- `game/src/ui/render.js`: imports legend helpers; new `renderPoison` (fills `#poison`, hides when null) and `renderLegend` (one `<li>` per row, `style.color` from row). Both called from `render()` and look up their elements inside the function.
- `game/index.html`: added `<p id="poison" hidden>` and `<ul id="legend">` after `#hud`, with CSS. Empty legend shows "No monsters in sight." via `:empty::before`.
- `game/src/ui/mock-game.js`: rat gets `ability: null`; `hud.poison: 0`; `visibleMonsters` returned from `getView` filtered to visible tiles, fields `kind, glyph, color, hp, maxHp, ability`.
- `game/test/legend.test.js` (new): 7 tests (row format, ability suffix, order, poison label, mock getView shape and visibility filter).
- Results: `node --check` passes on legend.js, render.js, mock-game.js. `node --test game/test/legend.test.js game/test/ui.test.js game/test/hud.test.js game/accept/e3-legend.test.js` gives 27 pass, 0 fail.
- Not touched: core/, data/, accept/, main.js. No change-log rows (no shared generator/config edits beyond the ones listed; mock-game is UI-only).

## In progress
- Nothing. Browser check is the lead's (no browser here).

## Next step
- Lead: run the browser check of the legend panel and poison label once `abilities` lands `hud.poison` and `visibleMonsters` in the real `core/game.js` getView. Until then the real game shows an empty legend and no poison label, because the real getView does not yet return the fields (mock-game does).

## Do not redo
- Ran the four-file test command above; passes. Do not re-run unless legend.js, render.js or mock-game.js changes.
- The rule "ability shown only when not null" is implemented as a truthiness check, so an undefined ability also gets no suffix.
