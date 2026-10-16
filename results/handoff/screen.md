# Handoff: screen (run e1, camera and inventory panel)

## Done
- `game/src/ui/camera.js` (new): `MIN_CELL = 16`, `cameraWindow(view, cols, rows)` per the e1 contract.
- `game/test/camera.test.js` (new): 7 tests (centre, clamp at each edge, small map, size cap, window inside map for every player tile, mock view has player and inventory).
- `game/src/ui/render.js`: draws only the camera window (`cols = min(view.w, floor(avail / MIN_CELL))`, `cell = floor(avail / cols)`, `rows = min(view.h, 15)`); sets `canvas.dataset.cell/cols/rows`; fills `#inventory` with one `button.small` per item (`data-action="use"`, `data-index`, label `<i+1> <glyph> <kind>`), or a `p.hint` reading `Inventory empty`. `MAX_CELL_W` removed (the contract defines the cell size from the width).
- `game/src/ui/mock-game.js` `getView`: returns `player: {x, y}` and `inventory` (kind, glyph, color, effect, amount).
- `game/index.html`: removed the `Use 1` button; added `<div id="inventory" class="actions" role="group" aria-label="Inventory">`; CSS `#inventory .hint { grid-column: span 2; }`.
- `game/src/ui/input.js`: NOT changed. Its click handler delegates on `document` and matches any `[data-action]`, so the dynamically rendered inventory buttons already reach `buttonToAction` (`index` parsed by `Number`). Keys 1-9 unchanged.
- Checks: `node --test game/test/camera.test.js game/test/ui.test.js game/accept/e1-camera.test.js` gives 23 pass, 0 fail. `node --check` passes on camera.js, render.js, mock-game.js, input.js, camera.test.js.
- Stub-DOM smoke run of `render()` (scratch, removed): canvas dataset `cell 16, cols 20, rows 14` at 328 px width; inventory shows `1 ! potion` with `data-index 0` after a pickup.

## In progress
- Nothing. Not started on any other file.

## Next step
- Lead: browser check on a phone-width viewport (about 360 px) and a desktop one. Confirm the canvas shows about 20 columns, the `#inventory` buttons appear under the pad, and tapping one drinks the potion. The real `core/game.js` must return `player` and `inventory` from `getView` (teammate `view`); until then `render()` throws on `view.inventory.length` if the field is missing.

## Do not redo
- Contract checks: the centring and clamp values in `camera.test.js` match the accept test in `game/accept/e1-camera.test.js`.
- Input delegation: no edit to `input.js` is needed (see Done).
- Canvas and DOM code are inside functions only; no DOM at import time.
