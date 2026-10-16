# Handoff: screen (e1 camera and inventory panel)

## Done
- `game/src/ui/camera.js` (new): `MIN_CELL = 16`, `cameraWindow(view, cols, rows)` -> `{ x0, y0, cols, rows }`, centred on `view.player`, clamped to the map. Falls back to map centre if `player` is missing.
- `game/src/ui/render.js`: new pure `layout(view, cssWidth)` -> `{ cols, rows, cell, cellH }` (cols = min(w, floor(width/16)), cell = floor(width/cols), rows = min(h, 15)). `render()` draws only the camera window, sets `canvas.dataset.cell/cols/rows`, and fills `#inventory` (one `button.small` per item with `data-action="use"`, `data-index`, label `<i+1> <glyph> <kind>`, or a "Inventory empty" note). HUD and log unchanged. Signature unchanged.
- `game/index.html`: added `<div id="inventory">` under the HUD, inventory CSS (2-column grid), removed the `Use 1` button.
- `game/src/ui/input.js`: `buttonToAction` for `use` returns null unless `data-index` is a non-negative integer. Taps on inventory buttons already reach `bindInput` through the delegated click handler; keys 1-9 unchanged.
- `game/src/ui/mock-game.js`: `getView` returns `player: {x, y}` and `inventory` (kind, glyph, color, effect, amount).
- `game/test/camera.test.js` (new): 10 tests (camera centring, clamps, small map, odd size, MIN_CELL, layout at 360 px, inventory button mapping, mock view fields).
- Results: `node --test game/test/camera.test.js game/test/ui.test.js game/accept/e1-camera.test.js` -> 25 pass, 0 fail. `node --check` passes on camera.js, render.js, input.js, mock-game.js, camera.test.js.
- Not touched: `game/src/core/`, `game/accept/`, `game/src/main.js`, shared files, `results/changes.md`.

## In progress
- Nothing. Browser check not done (no browser here; lead runs it).

## Next step
- Lead: once `view`'s `getView` returns `player` and `inventory` in `game/src/core/game.js`, run `npm run serve` and open http://localhost:8000/game/ at 360 px width. Check: canvas shows about 20 columns and is centred on `@`, nothing scrolls sideways, inventory buttons appear after picking up a potion, tapping one heals.
- Until then `main.js` still imports the mock, which already returns the new fields.

## Do not redo
- Camera window formulas match the ARCHITECTURE section and `game/accept/e1-camera.test.js` (all 5 pass). Do not change `cameraWindow` without re-running that file.
- `ui.test.js` passes unchanged with the new input and mock code.
- render.js has no import-time DOM. `document` is used only inside `render()` and `renderInventory()`.
