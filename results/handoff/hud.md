# Handoff: hud (e2: end screen and HP bar)

## Done
- `game/src/ui/hud.js` (new): `endMessage(view)` and `hpColor(hp, maxHp)`, pure, per the e2 contract.
- `game/test/hud.test.js` (new): 6 tests covering end messages (playing, dead, won) and the hpColor thresholds.
- `game/index.html`: added `#hpbar` with inner `#hpbar-fill` (between canvas and `#hud`); added `#end` panel (hidden attribute) with `#end-msg` and a `data-action="new"` New game button; CSS for the bar, panel and `#inventory .empty` (grid-column 1 / -1).
- `game/src/ui/render.js`: imports hud.js; new `renderHpBar` (fill width = clamped hp/maxHp, colour = hpColor) and `renderEnd` (panel shown when endMessage is non-null). Empty inventory is now a `<span class="empty">` so it spans the full width. `render()` signature unchanged; DOM is only touched inside functions.
- Checks: `node --check` on hud.js and render.js passes. `node --test game/test/hud.test.js game/test/ui.test.js game/test/camera.test.js game/accept/e2-hud.test.js` gives 27 tests, 27 pass, 0 fail.

## In progress
- Nothing. Browser check not done (no browser here; lead runs it).

## Next step
- Lead: open `game/index.html` in the browser (or `?seed=42`), check the HP bar shrinks and changes colour when hit, the end panel appears on death/win with the right text, and New game in the panel starts a new run.
- Lead: run `node --test game/test/hud.test.js game/test/ui.test.js game/test/camera.test.js game/accept/e2-hud.test.js` after merge.

## Do not redo
- Did not touch game/src/core/, game/src/data/, or game/accept/.
- Did not edit results/changes.md: index.html and render.js are UI files, not generators or configs (rule 13). Lead can add a row if it reads the rule more broadly.
- Did not change main.js; render() still receives (canvas, view, hudEl, logEl).
- Did not add a `hpFraction` helper; the ratio logic stays in render.js to match the contract's export list.
