# Run m0: base game, rules v0

Shakedown run, not an A/B. Base commit 85f0c78. Window starts 2026-10-16T19:58:30Z.
All teammates: `model: haiku`, `effort: medium`, `subagent_type: general-purpose`.

## Wave 1

### world

You are teammate `world` on the claude-team-a agent team; the lead is the main session. Follow the team rules in CLAUDE.md (already in your context).

Task: write game/src/core/rng.js, game/src/core/map.js and game/src/core/fov.js exactly to the contracts in game/ARCHITECTURE.md (sections core/rng.js, core/map.js, core/fov.js), with tests game/test/rng.test.js, game/test/map.test.js and game/test/fov.test.js.

Tests must cover: the same seed gives the same sequence and createRng(rng.state()) continues it; int() stays inside its bounds; for 20 seeds the map has a wall border, start and stairs in different rooms, and every FLOOR tile and the stairs are reachable from start (BFS); FOV includes the origin, includes a seen wall, and excludes a tile behind a wall.

Files you own: those six. Do not edit any other file. Other teammates are writing game/src/core/rules.js, game/src/data/ and game/src/ui/ at the same time.

Done when: `node --test game/test/rng.test.js game/test/map.test.js game/test/fov.test.js` passes.

Before your final message, write results/handoff/world.md (Done, In progress, Next step, Do not redo). Final message: one status line and the handoff path.

### rules

You are teammate `rules` on the claude-team-a agent team; the lead is the main session. Follow the team rules in CLAUDE.md (already in your context).

Task: write game/src/data/monsters.js, game/src/data/items.js and game/src/core/rules.js exactly to the contracts in game/ARCHITECTURE.md (sections data/monsters.js, data/items.js and core/rules.js), with tests in game/test/rules.test.js.

core/rng.js and core/map.js are being written right now by teammate `world`; do not import or edit them. In tests, build small maps by hand ({w, h, tiles, rooms, start, stairs} using '#', '.', '>') and use a fake rng object with next(), int(min, max) and pick(array), for example one that returns a fixed sequence.

Tests must cover: spawn counts; minDepth respected; spawns only on free FLOOR tiles (not start, stairs or occupied) and added to occupied; the attack damage formula with a known rng, and the killed flag; applyItem for heal (capped at maxHp), atk and def; monsterStep attacks when adjacent and visible, moves closer when visible, never moves onto a wall or a blocked tile, and does not mutate its inputs.

Files you own: those four. Do not edit any other file. Other teammates are writing game/src/core/rng.js, map.js, fov.js and game/src/ui/ at the same time.

Done when: `node --test game/test/rules.test.js` passes.

Before your final message, write results/handoff/rules.md (Done, In progress, Next step, Do not redo). Final message: one status line and the handoff path.

### ui

You are teammate `ui` on the claude-team-a agent team; the lead is the main session. Follow the team rules in CLAUDE.md (already in your context).

Task: write the browser UI per the "UI" section of game/ARCHITECTURE.md: game/index.html, game/src/main.js, game/src/ui/render.js, game/src/ui/input.js and game/src/ui/mock-game.js, plus game/test/ui.test.js.

core/game.js does not exist yet. mock-game.js exports newGame(seed), act(state, action) and getView(state) returning the exact View shape from the core/game.js section of the contract (fake data is fine: a small room the player can walk around, one monster, a log line per action). main.js imports from ./ui/mock-game.js.

The page must work on a phone: the canvas scales to the screen width (360 px and up), an on-screen d-pad plus buttons (wait, pick up, descend, new game), no horizontal scroll, dark background. Keyboard controls as listed in the contract.

There is no browser here. Verify with `node --check` on each .js file, and with game/test/ui.test.js, which imports mock-game.js and checks that newGame/act/getView return the contract shapes (cells length is w*h, hud fields present, log at most 5 lines). Keep DOM code out of that test: render.js and input.js touch the DOM only inside their functions, never at import time.

Files you own: those six. Do not edit any other file. Other teammates are writing game/src/core/ and game/src/data/ at the same time.

Done when: `node --test game/test/ui.test.js` passes and `node --check` passes for every .js file you wrote.

Before your final message, write results/handoff/ui.md (Done, In progress, Next step, Do not redo). Final message: one status line and the handoff path.

## Merge check after wave 1

`npm test`: 62 pass, 0 fail. Change log empty. Handoffs: world, rules, ui present.

## Wave 2

### game

You are teammate `game` on the claude-team-a agent team; the lead is the main session. Follow the team rules in CLAUDE.md (already in your context).

Task: write game/src/core/game.js exactly to the core/game.js section of game/ARCHITECTURE.md, with tests in game/test/game.test.js, then switch game/src/main.js to the real game.

Wave 1 is done and merged: core/rng.js, core/map.js, core/fov.js, core/rules.js, data/*.js and the UI exist and their tests pass. Use their exports as they are; do not edit them. First read the Done and Next step sections of results/handoff/world.md, rules.md and ui.md: they list details you need (entity ids, the 0-based `use` index, the exact import line to change in main.js).

Tests must cover: newGame(seed) is deterministic and puts the player on map.start with status 'playing'; moving into a wall costs no turn; moving into a monster attacks it; killing a monster removes it and adds xp, and 10 xp levels up (+5 maxHp, +1 atk); pickup and use of an item; descend works only on stairs, keeps stats and inventory, and on MAX_DEPTH sets 'won'; hp at 0 or below sets 'dead' and later actions are ignored; getView returns w*h cells, the player glyph on the player tile, ' ' on unexplored tiles and at most 5 log lines; a 200-turn random walk on 5 seeds never throws.

Files you own: game/src/core/game.js, game/test/game.test.js, and the one import line in game/src/main.js. Do not edit any other file. If you think another module has a bug, write it in your handoff instead of fixing it.

Done when: `node --test game/test/game.test.js game/test/ui.test.js` passes.

Before your final message, write results/handoff/game.md (Done, In progress, Next step, Do not redo). Final message: one status line and the handoff path.

## Merge check after wave 2

`npm test`: 78 pass, 0 fail. Change log empty. Note: `game` ran the full suite itself (v0 reserves full runs for the lead).

## Wave 3

### sim

You are teammate `sim` on the claude-team-a agent team; the lead is the main session. Follow the team rules in CLAUDE.md (already in your context).

Task: write game/sim/bot.mjs per the sim/bot.mjs section of game/ARCHITECTURE.md, plus game/sim/seeds-sample.txt (5 seeds, one per line) and game/test/bot.test.js.

The game is done and merged. Use newGame, act and getView from game/src/core/game.js as they are; read the Done section of results/handoff/game.md first. Do not edit any file except the three you own.

Bot policy (simple and greedy): attack an adjacent monster; if hp is below 40% of maxHp and the inventory holds a heal item, use it; if standing on an item, pick it up; if the stairs tile is explored, walk to it by BFS over explored walkable tiles and descend there; otherwise walk to the nearest explored walkable tile next to an unexplored one; if none of that applies, wait.

Export `chooseAction(state)` and `playGame(seed, maxTurns)` so the test can import them without running the command line part (guard it with `import.meta.url === pathToFileURL(process.argv[1]).href`). Output JSON: { seeds: [{ seed, status, depth, turns, level, killedBy }], summary: { games, winRate, meanDepth, meanTurns, deathsByKind } }. killedBy is the kind of monster that landed the killing blow, or null; if game.js doesn't expose it, take it from the log or leave it null and say so in your handoff.

Run only the sample (rule 10): `node game/sim/bot.mjs --seeds game/sim/seeds-sample.txt --out scratch/sim/sample.json`. The lead runs the full job on game/sim/seeds-200.txt.

Tests: chooseAction returns a valid action for 3 seeds at turn 0; playGame ends (dead, won or maxTurns) for 3 seeds with maxTurns 2000, and gives the same result twice for the same seed.

Done when: `node --test game/test/bot.test.js` passes and the sample run wrote scratch/sim/sample.json.

Before your final message, write results/handoff/sim.md (Done, In progress, Next step, Do not redo). Final message: one status line and the handoff path.
