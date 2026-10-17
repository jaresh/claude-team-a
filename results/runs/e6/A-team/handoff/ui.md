# Handoff: ui (shop, e6)

## Done
- `game/src/ui/input.js`: `buttonToAction` maps `data-action="buy"` + `data-index` to `{type:'buy', index}`. Shares the `use` case, so a missing or non-integer index is still null. `bindInput` comment mentions shop buttons.
- `game/src/ui/render.js`:
  - HUD text gains `GOLD ${h.gold}` after XP.
  - New exported pure helper `shopRows(shop)`: `[]` unless `shop.open`; otherwise `{index, text: "<glyph> <kind> <price>g"}` per stock row.
  - New `renderShop` fills `#shop` and toggles its `hidden` from `view.shop.open`. It writes a "Shop" title, then one `button.small` per row with `data-action="buy"` and `data-index=<stock index>`. It shows "Nothing for sale" if the stock is empty.
  - `render()` calls `renderShop(document.getElementById('shop'), view.shop)`.
- `game/index.html`: `<div id="shop" role="group" aria-label="Shop" hidden>` after `#inventory`, with CSS (`#shop[hidden]` hides it; title in gold, `.empty` in grey). There is no separate `#gold` element; gold is in the HUD text, which the contract allows.
- `game/src/ui/mock-game.js`: player `gold: 0`; `hud.gold`; `shop` from a new `shopView(state)` (open when the player is on `map.start`, stock is 3 fixed rows with `index` 0..2 and the full contract row shape); the start tile renders as `$` (`#fbbf24` when visible, dim when only explored) after items. `buy` is not implemented in the mock. It falls through to the existing "Unknown action" log.
- `game/test/shopui.test.js` (new): 8 tests covering `shopRows`, buy button mapping (valid and invalid index), `bindInput` click dispatch to `{type:'buy', index}` through a fake root, and the mock's gold, shop open/closed, indexed stock and `$` cell.
- `main.js`: no change needed. `buy` goes through `bindInput` to `act()` and then `draw()`, the same as other actions.
- Did not touch: core/, data/, accept/, help.js, hud.js.

Check: `node --test game/test/ui.test.js game/test/shopui.test.js game/test/hud.test.js game/test/legend.test.js game/test/help.test.js` gives 36 tests, 36 pass, 0 fail. `node --check` passes on render.js, input.js and mock-game.js.

## In progress
Nothing. The task is complete. Not committed (per team rules).

## Next step
None for ui. The lead can launch the game (`game/index.html` via the usual dev/serve command) and check the shop panel in a browser. The node tests cannot exercise the real DOM path of `render()`/`renderShop()`, only the pure helpers.

## Do not redo
- The shop is open at turn 0 because the player starts on `map.start`. The first version of the "closed" mock test failed for that reason; it now moves the player off the tile first.
- `help.js` `glyphRows` has a test asserting exactly two base rows for an empty trap list. Adding a shop row there would break `help.test.js`, so I did not add one (and `help.js` is not mine to edit).
- `ui.test.js` only checks the view shape loosely (it doesn't require `gold` or `shop`), so it passes unchanged; I did not edit it.
