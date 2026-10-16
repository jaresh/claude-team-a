# Handoff: view (run e1, getView player and inventory)

## Done
- `game/src/core/game.js` `getView`: added `player: { x, y }` and `inventory` (mapped from `p.inventory` to `{ kind, glyph, color, effect, amount }`, in inventory order). Nothing else in game.js changed.
- `game/test/view.test.js` created: 6 tests (player tile, player position follows state, empty inventory, inventory order and fields, only view fields present, returned inventory does not alias player items).
- Check: `node --test game/test/view.test.js game/test/game.test.js game/accept/e1-view.test.js` gives 25 tests, 25 pass, 0 fail.
- No edits to `game/src/ui/`, `game/index.html`, `game/src/main.js`, or `game/accept/`. No changelog row in `results/changes.md` was written (not in my task list; lead to decide whether `game.js` getView counts as a shared-generator edit under rule 13).

## In progress
- Nothing. Task complete.

## Next step
- Lead merges. `screen` teammate consumes `view.player` and `view.inventory` for the camera and inventory panel.

## Do not redo
- The e1 view acceptance tests (`game/accept/e1-view.test.js`) already pass with this change; no need to re-run beyond the combined check above.
- No other getView behaviour was touched; the `cells`, `hud`, `log` and `status` fields are unchanged.
