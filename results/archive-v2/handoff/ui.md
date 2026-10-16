# Handoff: ui

## Done
- `game/index.html`: dark page, viewport meta, no horizontal scroll, canvas, HUD, log (5 lines), d-pad (3x3, centre = Wait), buttons Pick up, Use 1, Descend, New game.
- `game/src/main.js`: wires `newGame` / `act` / `getView` to `render`, `bindInput`; seed from `?seed=` (numeric or string), else random; `new` action makes a new random game; redraws on window resize.
- `game/src/ui/render.js`: `render(canvas, view, hudEl, logEl)`. Canvas width = parent width (fallback `innerWidth - 32`), cell width capped at 24 css px, HiDPI aware. HUD text line and log `<li>` items.
- `game/src/ui/input.js`: `bindInput(root, onAction)` returns an unbind function. Exports pure helpers `keyToAction(key)` and `buttonToAction(dataset)`. Keys: arrows, WASD, hjkl, yubn, `.`, `g`, `>`, `1`-`9` (use, 0-based index). Ignores keys with ctrl/meta/alt or from inputs.
- `game/src/ui/mock-game.js`: exports `MAX_DEPTH`, `FOV_RADIUS`, `newGame`, `act`, `getView`. One 24x14 room with a pillar, one rat, one potion, stairs at a corner. Square-radius FOV (not shadowcasting). Each accepted action logs a line; blocked moves cost no turn.
- `game/test/ui.test.js`: 11 tests, all pass (`node --test game/test/ui.test.js`).
- `node --check` passes on all four .js files in `game/src/ui/` and `game/src/main.js`, and on the test.
- Not touched: any other file. No changes to `results/changes.md` (no shared file edited).

## In progress
- Nothing. Browser behaviour has not been checked (no browser here).

## Next step
- Wave 2 (game owner): in `game/src/main.js` change line 1 from `import { newGame, act, getView } from './ui/mock-game.js';` to `from '../src/core/game.js'` (path is relative to `game/src/main.js`, so `./core/game.js`). Then run `node --test game/test/ui.test.js`. Note that test imports `../src/ui/mock-game.js` directly, so keep the mock file or point the test at core/game.js too.
- Check the core `use` action index is 0-based (main.js and input.js assume it). If core uses 1-based, change `keyToAction` (`Number(k) - 1`) and the `Use 1` button `data-index`.
- Lead, manual check when a browser is available: `npm run serve`, open http://localhost:8000/game/ at 360 px width, confirm the canvas fits and nothing scrolls sideways.

## Do not redo
- Node syntax check and the UI test already pass. Re-running them is only needed after the core import switch.
- The earlier test failure (log length check at the 50-line cap) was a test bug, not a mock bug. It is fixed by clearing `state.log` before each action in the test.
- The mock's `act` returns the same object it was given, which matches the contract ("mutates and returns it").
