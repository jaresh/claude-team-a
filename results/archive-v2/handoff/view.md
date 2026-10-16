# Handoff: view (run e1, variant B)

## Done
- `game/src/core/game.js` `getView`: added `player: { x, y }` and `inventory` (entries
  `{ kind, glyph, color, effect, amount }` in inventory order, copied, not live references).
  No other change to game.js.
- `game/test/view.test.js`: new file, 4 tests (player tile, inventory order and fields,
  empty inventory, inventory is a copy).
- `node --test game/test/view.test.js game/test/game.test.js game/accept/e1-view.test.js`:
  23 pass, 0 fail.
- Did not touch `game/src/ui/`, `game/index.html`, `game/src/main.js`, `game/accept/`.
- `results/changes.md` not edited (the contract change is in the e1 section; log it if the lead wants one line per edit: game.js, getView, added player and inventory fields).

## In progress
- Nothing.

## Next step
- Lead: log the change in `results/changes.md` (date, view, game/src/core/game.js, getView, player and inventory fields).
- Lead: `node --test game/test/view.test.js game/test/game.test.js game/accept/e1-view.test.js` for the merge check.

## Do not redo
- The three-file test run above already passes; no need to rerun before merge unless game.js changes again.
- `game/test/view.test.js` did not exist before this task; it was created, not extended.
