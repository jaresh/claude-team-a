# Team status

Kept by the lead (rule 19). Update when a teammate starts, hands off or stops, and when a job
starts or finishes.

## Teammates

| Name | Task | Model | Effort | State | Handoff |
|---|---|---|---|---|---|
| world | M0 wave 1: core/rng.js, core/map.js, core/fov.js + tests | haiku | medium | done (33/33 tests) | results/handoff/world.md |
| rules | M0 wave 1: data tables, core/rules.js + tests | haiku | medium | done (18/18 tests) | results/handoff/rules.md |
| ui | M0 wave 1: index.html, main.js, ui/*, mock-game.js + test | haiku | medium | done (11/11 tests) | results/handoff/ui.md |
| game | M0 wave 2: core/game.js + tests, main.js switch to real game | haiku | medium | done (16 tests; 78/78 merged) | results/handoff/game.md |
| sim | M0 wave 3: sim/bot.mjs + test, 5-seed sample | haiku | medium | done (3/3 tests, sample ok) | results/handoff/sim.md |
| view | e1-B: getView player + inventory, test/view.test.js (start 2026-10-16T20:39:02Z) | haiku (dev) | medium | done (23/23; merged 91/91 + accept 8/8 + smoke ok) | results/handoff/view.md |
| screen | e1-B: ui/camera.js, render.js, index.html, input.js, mock-game.js + camera test | haiku (dev) | medium | done (22/22; merged 91/91 + accept 8/8 + smoke ok) | results/handoff/screen.md |

## Background jobs

| What | Output file | Done check | State |
|---|---|---|---|
| M0 bot run, 200 seeds (lead) | out/sim/m0/full.json | file has `summary.games == 200` | done (0.8 s) |
