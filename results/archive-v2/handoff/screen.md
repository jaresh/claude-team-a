# Handoff: screen (run e1, variant B)

## Done
- `game/src/ui/camera.js` (new): `MIN_CELL = 16`, `cameraWindow(view, cols, rows)` per the e1 contract.
- `game/test/camera.test.js` (new): 6 tests (edge clamping on all tiles, player always inside window, large map, small map, odd window centring, MIN_CELL).
- `game/src/ui/render.js`: draws only the camera window; `cols = max(1, min(view.w, floor(avail / 16)))`, `cell = floor(avail / cols)`, `rows = min(view.h, 15)`; sets `canvas.dataset.cell/cols/rows`; fills `#inventory` (buttons `data-action="use"`, `data-index`, label `<i+1> <glyph> <kind>`, or `Inventory empty`). `#inventory` is looked up inside `render()` so the signature is unchanged and `main.js` needs no edit.
- `game/index.html`: removed the `Use 1` button; added `<div id="inventory" role="group" aria-label="Inventory">` after the actions group; CSS for `#inventory` as a 2-column grid.
- `game/src/ui/input.js`: `buttonToAction` `use` case returns null unless `data-index` is a non-empty integer (the generic `[data-action]` click delegation already covers dynamically added inventory buttons; comment added). Keys 1-9 unchanged.
- `game/src/ui/mock-game.js`: `getView` returns `player: {x, y}` and `inventory` (kind, glyph, color, effect, amount).
- Checks: `node --test game/test/camera.test.js game/test/ui.test.js game/accept/e1-camera.test.js` → 22 pass, 0 fail. `node --check` passes on camera.js, render.js, input.js, mock-game.js. Stub-DOM smoke run (scratch only) of `render()` with a moved player: dataset cell 16 / cols 22 / rows 14, no exception.
- No edits to `game/src/core/`, `game/accept/`, `main.js`, or `results/changes.md` (not a shared generator).

## In progress
- Nothing. Browser check not done (no browser here; lead runs it).

## Next step
- Lead: open `game/index.html` in a phone-width viewport and confirm the map draws centred on the player, and that tapping an inventory button after a pickup (`g` on the potion) calls use. Needs `getView` to supply `player` and `inventory` from `game/src/core/game.js` (the `view` teammate's work) when `main.js` imports core instead of the mock.

## Do not redo
- Acceptance and camera unit tests: already passing (22/22); re-run only after a change to camera.js or render.js.
- Syntax checks: already passing for the four files above.
- Note for lead: `game/src/main.js` currently imports `./core/game.js`, not the mock, so the mock change matters only if the import is switched back.
