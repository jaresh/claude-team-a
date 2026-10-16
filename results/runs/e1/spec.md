# Run e1: phone camera and inventory panel

A/B run per `kit/protocol/experiments.md`. Base: tag `run/e1/base`.
Variant A uses rules v0 (branch `run/e1/A`); variant B uses rules v1 (branch `run/e1/B`).

## Feature

The 60x30 map is drawn at about 5 px per tile on a phone. Draw only a window around the player,
with tiles at least 16 px, and show the inventory as tappable buttons. Contract: sections
"e1: View additions" and "e1: camera and inventory panel" in `game/ARCHITECTURE.md`.

## Acceptance (lead runs it once, after the merge)

```
npm test && node --test "game/accept/*.test.js" && node game/tools/smoke.mjs out/e1/<variant>.png
```

All three must pass. The base fails the last two (4 acceptance tests fail; smoke fails
`cellAtLeast16` and `inventoryPanel`).

## Lead steps

1. `git checkout run/e1/<variant>`, note the start time (`date -u +%FT%TZ`).
2. Start `view` and `screen` in parallel with the prompts below, word for word, `model: haiku`,
   `effort: medium`, and the agent type the rules name.
3. When both have handed back: merge check as the rules say, then the acceptance command.
4. Note the end time. Run
   `python3 kit/tools/teamcost.py --since <start> --until <end> --json results/metrics/e1-<variant>.json`
5. Add a row to `results/experiments.md`, commit on the branch, push.

## Teammate prompts

### view

You are teammate `view` on the claude-team-a agent team; the lead is the main session. Follow the team rules in CLAUDE.md (already in your context).

Task: extend getView in game/src/core/game.js with the `player` and `inventory` fields from the "e1: View additions" section of game/ARCHITECTURE.md, with tests in game/test/view.test.js.

Teammate `screen` is changing the UI at the same time: do not edit game/src/ui/, game/index.html or game/src/main.js. Do not change any other behaviour of game.js. Do not edit game/accept/.

Done when: `node --test game/test/view.test.js game/test/game.test.js game/accept/e1-view.test.js` passes.

Before your final message, write results/handoff/view.md (Done, In progress, Next step, Do not redo). Final message: one status line and the handoff path.

### screen

You are teammate `screen` on the claude-team-a agent team; the lead is the main session. Follow the team rules in CLAUDE.md (already in your context).

Task: make the game playable on a phone per the "e1: camera and inventory panel" section of game/ARCHITECTURE.md. Write game/src/ui/camera.js with tests in game/test/camera.test.js; change game/src/ui/render.js to draw only the camera window and fill the inventory panel; update game/index.html, game/src/ui/input.js and game/src/ui/mock-game.js as that section says.

Teammate `view` is adding `player` and `inventory` to getView in game/src/core/game.js at the same time: do not edit game/src/core/. Do not edit game/accept/. There is no browser for you; the lead runs the browser check. Keep DOM code inside functions, never at import time.

Done when: `node --test game/test/camera.test.js game/test/ui.test.js game/accept/e1-camera.test.js` passes and `node --check` passes for every .js file you changed.

Before your final message, write results/handoff/screen.md (Done, In progress, Next step, Do not redo). Final message: one status line and the handoff path.
