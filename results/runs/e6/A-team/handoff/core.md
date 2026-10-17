# Handoff: core

## Done
- `game/src/data/shop.js` (new): `SHOP_STOCK` (4 rows: potion 10g d1, whetstone 15g d1, ring 25g d2, great potion 30g d4) and `goldFor(row, depth)` = `max(1, xp) * 2 + depth`.
- `game/src/core/game.js`:
  - `player.gold` starts at 0, kept across levels.
  - Kill gives `goldFor` gold and logs `You find <n> gold.`
  - `act` case `buy`: checks shop tile, then index (into current stock, minDepth <= depth), then gold. Success pushes a stock item (negative id, `x:0, y:0`) into inventory, logs `You buy a <kind>.`, takes no turn. Failures log `There is no shop here.`, `Nothing like that is for sale.`, or `You need <price> gold.`
  - `getView`: `hud.gold`, `shop: {x, y, open, stock}` (stock empty unless open). Shop tile cell is `$` (`#fbbf24` when visible, dim when only explored) after trap in cell order.
- `game/test/shop.test.js` (new): 16 unit tests.
- `.claude/team/changes.md`: one line appended.

## Check results
- `node --test game/test/shop.test.js game/test/game.test.js game/accept/e6-shop.test.js game/accept/e2-balance.test.js`: 42 pass, 0 fail.
- `npm test` (full): 159 run, 153 pass, 6 fail at the time of the run: help.test.js "mock view: traps are listed only when in sight", scores.test.js (3 mock-game tests), ui.test.js "getView returns the contract shape" and "many actions keep the view valid...". Re-running ui.test.js, help.test.js and scores.test.js alone gives 31 pass, 0 fail. The UI teammate was editing mock-game.js, index.html, input.js and render.js in the same checkout during my run, so these failures look transient from that work, not from game.js. Not verified further; the lead should re-run `npm test` after the ui task finishes.

## In progress
- Nothing. Core task complete.

## Next step
- Lead: after the ui task, run `npm test && node --test game/accept/`. If the ui.test.js / scores.test.js / help.test.js failures persist, check `game/src/ui/mock-game.js` (the fake core) for missing `hud.gold` / `shop` fields. That file is UI-owned, so it is not mine to edit.

## Do not redo
- Checked the `buy` order: tile check first, then index, then gold. The e6 accept tests need the no-gold and bad-index cases to leave state unchanged, and they do.
- Confirmed `spawnFrom` never places items or monsters on `map.start`, so the shop tile is never occupied.
- Did not touch accept/, UI files, rules.js, monsters/items data, or sim/.
