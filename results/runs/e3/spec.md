# Run e3: monster abilities and monster legend

A/B run per `kit/protocol/experiments.md`. Base: tag `run/e3/base`. Rules v2.1 and the v2.1 run
lead (Sonnet 5.5, effort medium, 1-hour cache) in both variants. The variable is a hard cap on
Haiku teammates' context:

| Variant | Start command | Haiku teammates |
|---|---|---|
| A | `kit/run.sh --bg results/runs/e3/spec.md A` | no cap |
| B | `EXTRA_SETTINGS='{"modelSettings":{"claude-haiku-5-5":{"autoCompactWindow":100000}}}' kit/run.sh --bg results/runs/e3/spec.md B` | auto-compact at a 100K window |

The cap only matters if a teammate's context nears 100K, so the `abilities` task is larger than
earlier tasks: three game mechanics, tests, and a balance re-check.

## Feature

1. **Monster abilities**: regeneration, poison and ranged attacks, keeping the e2 balance
   targets. Contract: "e3: monster abilities" in `game/ARCHITECTURE.md`.
2. **Monster legend**: the monsters in sight with their hp and ability, and a poison label.
   Contract: "e3: monster legend" in `game/ARCHITECTURE.md`.

## Acceptance (lead runs it once, after the merge)

```
npm test && node --test "game/accept/*.test.js" && node game/tools/smoke.mjs out/e3/<variant>.png --ids inventory,hpbar,end,legend
```

All three must pass. The base fails the last two.

## Lead steps

1. In one turn: update `results/team-status.md` (one row per teammate) and start `abilities` and
   `legend` in parallel with the prompts below, word for word: agent type `dev`,
   `model: "haiku"`, `effort: "medium"`. Then end the turn (L3).
2. When both have handed back, in one turn: read `results/changes.md` and the handoffs' Done and
   Next step (L4), then run the acceptance command.
3. If acceptance fails, one fix round: start a successor for the failing part (`abilities-2` or
   `legend-2`, rule 6) with the failing output, or fix a one-line problem yourself. Then run the
   acceptance command once more.
4. In one turn: write `date -u +%FT%TZ` to your end-time file (named in your first message),
   write `results/runs/e3/<variant>.md` (at most 5 lines: acceptance result, fix rounds,
   successors, anything odd), update the status file, commit everything on the branch, push.
5. Tell the user: "Run done. Type /exit; kit/run.sh will measure it."

## Teammate prompts

### abilities

You are teammate `abilities` on the claude-team-a agent team; the lead is the main session. Follow the team rules in CLAUDE.md (already in your context).

Task: add monster abilities per the "e3: monster abilities" section of game/ARCHITECTURE.md, in game/src/data/monsters.js, game/src/core/rules.js and game/src/core/game.js, with tests in game/test/abilities.test.js. Then check the balance with `node --test game/accept/e2-balance.test.js`; if a target fails, re-tune using only the changes the "e2: balance" section allows. Log each change to a shared table or tuning constant in results/changes.md (rule 13).

Teammate `legend` is changing game/src/ui/ and game/index.html at the same time: do not edit those. Do not edit game/sim/ or game/accept/.

Done when: `node --test game/test/abilities.test.js game/test/rules.test.js game/test/game.test.js game/accept/e3-abilities.test.js game/accept/e2-balance.test.js` passes.

Before your final message, write results/handoff/abilities.md (Done, In progress, Next step, Do not redo). Final message: one status line and the handoff path.

### legend

You are teammate `legend` on the claude-team-a agent team; the lead is the main session. Follow the team rules in CLAUDE.md (already in your context).

Task: add the monster legend and the poison label per the "e3: monster legend" section of game/ARCHITECTURE.md. Write game/src/ui/legend.js with tests in game/test/legend.test.js; update game/index.html, game/src/ui/render.js and game/src/ui/mock-game.js as that section says.

Teammate `abilities` is changing game/src/core/ and game/src/data/ at the same time: do not edit those. Do not edit game/accept/. There is no browser for you; the lead runs the browser check. Keep DOM code inside functions, never at import time.

Done when: `node --test game/test/legend.test.js game/test/ui.test.js game/test/hud.test.js game/accept/e3-legend.test.js` passes and `node --check` passes for every .js file you changed.

Before your final message, write results/handoff/legend.md (Done, In progress, Next step, Do not redo). Final message: one status line and the handoff path.
