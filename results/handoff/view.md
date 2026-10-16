# Handoff: view (e1-A: getView player + inventory)

## Done
- `game/src/core/game.js`: `getView` returns `player: { x, y }` and `inventory` (list of `{ kind, glyph, color, effect, amount }`, in inventory order, copied so the view does not alias `player.inventory`). Nothing else in game.js changed.
- `game/test/view.test.js`: new, 5 tests (player position, inventory order and fields, empty inventory, copy semantics, pickup/use reflected in view).
- `results/changes.md`: one line appended for the getView edit.
- Check: `node --test game/test/view.test.js game/test/game.test.js game/accept/e1-view.test.js` -> 24 pass, 0 fail.

## In progress
- Nothing. Task complete.

## Next step
- Lead: after merge, run `node --test game/test/view.test.js game/test/game.test.js game/accept/e1-view.test.js` and `npm test`.
- Screen teammate reads `player` and `inventory` from the view; the field shapes are as in ARCHITECTURE.md e1 section.

## Do not redo
- Did not touch game/src/ui/, game/index.html, game/src/main.js, game/accept/, or ARCHITECTURE.md.
- Inventory entries deliberately omit `id`, `x`, `y` (the e1 contract lists only the five fields); the accept test checks presence of those five keys.
