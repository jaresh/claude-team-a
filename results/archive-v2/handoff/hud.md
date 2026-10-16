# Handoff: hud (e2: end screen and HP bar)

## Done
- `game/src/ui/hud.js` (new): `endMessage(view)` and `hpColor(hp, maxHp)` per the ARCHITECTURE.md
  e2 section. Pure, no DOM.
- `game/test/hud.test.js` (new): 6 tests covering playing/dead/won messages and the three HP colour bands.
- `game/src/ui/render.js`: imports hud.js; `renderHpBar` sets `#hpbar .fill` width to hp/maxHp
  (clamped 0..1) and colour from `hpColor`; `renderEnd` sets `#end` hidden unless `endMessage`
  is non-null, and writes the message into `.end-text`. Empty inventory text is now a
  `<span class="empty">` so it can span the grid.
- `game/index.html`: `#hpbar` (outer, with inner `.fill`) above `#hud`; `#end` (hidden by default,
  with `.end-text` and a `data-action="new"` New game button) above the move pad; CSS for both,
  and `#inventory .empty { grid-column: 1 / -1 }`.
- Checks: `node --test game/test/hud.test.js game/test/ui.test.js game/test/camera.test.js game/accept/e2-hud.test.js`
  gives 27 pass, 0 fail. `node --check` passes on hud.js, render.js and hud.test.js.
- Not touched: core/, data/, accept/, input.js, main.js, mock-game.js, changes.md (no shared generator or config edited).

## In progress
- Nothing. Browser check not run (no browser here; the lead runs it).

## Next step
- Lead: open `game/index.html` in a browser, play to death or win, and confirm: the HP bar shrinks
  and changes colour, `#end` appears with the message, and its New game button starts a new game
  (the button is caught by the document-level `bindInput`, the same path as the existing button).
- Also confirm the empty inventory text fills the panel width on one line.

## Do not redo
- Node tests above already pass; no need to rerun them unless the files change.
- `#end` uses the `hidden` attribute with an explicit `#end[hidden]{display:none}` rule, so the
  panel's own `display` is never set in CSS and cannot override it.
