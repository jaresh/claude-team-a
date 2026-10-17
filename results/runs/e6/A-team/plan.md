# Plan: shop (e6)
Goal: monsters drop gold; each level has a shop where gold buys items. Check: `npm test && node --test game/accept/` (incl. lead's game/accept/e6-shop.test.js, e2 balance must still pass).

## Assumptions
Shop = the level's start tile (shown as `$` when the player is elsewhere). Stock is unlimited, filtered by minDepth. Gold per kill is deterministic (no rng, so balance is unchanged). Buying takes no turn. Bought items go into the inventory (use as normal).

## Contract
`game/src/data/shop.js`:
```js
export const SHOP_STOCK = [{ kind, glyph, color, effect: 'heal'|'atk'|'def', amount, price, minDepth }]; // >=3 rows; appended later only
export function goldFor(monsterRow, depth) // -> integer >=1: Math.max(1, monsterRow.xp) * 2 + depth
```
`game.js`: `player.gold` (starts 0, kept across levels). Killing a monster: `player.gold += goldFor(monster, state.depth)`, log `You find <n> gold.` New action `{type:'buy', index}`: `index` is the index into the CURRENT stock (SHOP_STOCK rows with minDepth <= depth, in table order). Valid only if the player stands on `map.start` (shop tile), index valid, gold >= price: gold -= price, push `{id, kind, glyph, color, effect, amount, x:0, y:0}` into inventory, log `You buy a <kind>.`; takes NO turn (no monster phase, turn unchanged). Otherwise log a reason (`You need <price> gold.` / `There is no shop here.`) and nothing else changes.
`getView` adds `hud.gold` and `shop: { x, y, open: bool (player on start tile), stock: [{index, kind, glyph, color, effect, amount, price}] (empty when not open) }`. Cell order: player, monster, item, trap, then the shop tile shows `{ch:'$', fg:'#fbbf24'}` when visible (or explored: dim) instead of the floor glyph; then tile.
UI: `index.html` gets `#shop` panel (hidden unless `view.shop.open`), one button per stock entry with `data-action="buy"` and `data-index="<index>"`, labelled `<glyph> <kind> <price>g`; `#gold` element shows gold (HUD text also fine). `input.js` maps taps on `[data-action=buy]` to `{type:'buy', index}`; `b` key not needed. `mock-game.js` returns `hud.gold` and `shop` too.

## core
Owns: game/src/data/shop.js (new), game/src/core/game.js, game/test/shop.test.js (new unit tests).
Do: implement the Contract's data and game logic. May change: only those files (plus appending a line to changes.md). Must not touch: accept/, UI files, rules.js, monsters/items data, sim/. Done: `node --test game/test/shop.test.js game/test/game.test.js game/accept/e6-shop.test.js game/accept/e2-balance.test.js`.

## ui
Owns: game/index.html, game/src/ui/render.js, game/src/ui/input.js, game/src/ui/mock-game.js, game/test/shopui.test.js (new). Also main.js if the wiring needs it.
Do: the UI part of the Contract; look at existing ui.test.js for how DOM is faked and keep it passing; add unit tests. Must not touch: core/, data/, accept/. Done: `node --test game/test/ui.test.js game/test/shopui.test.js game/test/hud.test.js game/test/legend.test.js game/test/help.test.js`.
