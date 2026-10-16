# Run e2: balance, end screen and HP bar

A/B run per `kit/protocol/experiments.md`. Base: tag `run/e2/base`. Rules v2 in both variants.
The variable is the run lead's settings:

| Variant | Start command | Lead |
|---|---|---|
| A | `LEAD_MODEL=opus LEAD_EFFORT=xhigh CACHE_TTL=1h kit/run.sh results/runs/e2/spec.md A` | Opus 5.5, xhigh, 1-hour cache (as in e1-B) |
| B | `kit/run.sh results/runs/e2/spec.md B` | Sonnet 5.5, medium, 5-minute cache (v2 defaults) |

## Feature

1. **Balance.** The bot never wins (0 of 200 seeds, mean depth 2.3; goblins cause 60% of
   deaths). Tune the numbers so the game is winnable but hard. Contract: "e2: balance" in
   `game/ARCHITECTURE.md`.
2. **End screen and HP bar.** Contract: "e2: end screen and HP bar" in `game/ARCHITECTURE.md`.

## Acceptance (lead runs it once, after the merge)

```
npm test && node --test "game/accept/e2-*.test.js" && node game/tools/smoke.mjs out/e2/<variant>.png --ids inventory,hpbar,end
```

All three must pass. The base fails the last two.

## Lead steps

1. In one turn: update `results/team-status.md` (one row per teammate) and start `tuner` and `hud`
   in parallel with the prompts below, word for word: agent type `dev`, `model: "haiku"`,
   `effort: "medium"`. Then end the turn (L3).
2. When both have handed back, in one turn: read `results/changes.md` and the handoffs' Done and
   Next step (L4), then run the acceptance command.
3. If acceptance fails, one fix round: start a successor for the failing part (`tuner-2` or
   `hud-2`, rule 6) with the failing output, or fix a one-line problem yourself. Then run the
   acceptance command once more.
4. In one turn: write `date -u +%FT%TZ` to your end-time file (named in your first message),
   write `results/runs/e2/<variant>.md` (at most 5 lines: acceptance result, fix rounds, anything
   odd), update the status file, commit everything on the branch, push.
5. Tell the user: "Run done. Type /exit; kit/run.sh will measure it."

## Teammate prompts

### tuner

You are teammate `tuner` on the claude-team-a agent team; the lead is the main session. Follow the team rules in CLAUDE.md (already in your context).

Task: balance the game to the targets in the "e2: balance" section of game/ARCHITECTURE.md, changing only what that section allows. Log each change in results/changes.md (rule 13).

Measure with `node --test game/accept/e2-balance.test.js` (about 1 s; a failing target prints the measured value). Change a few numbers at a time and measure after each change. Teammate `hud` is changing game/src/ui/ and game/index.html at the same time: do not edit those. Do not edit game/sim/ or game/accept/.

Done when: `node --test game/accept/e2-balance.test.js game/test/rules.test.js game/test/game.test.js` passes. If a unit test asserts an old number that you changed on purpose (for example a spawn count), update that assertion and say so in your handoff.

Before your final message, write results/handoff/tuner.md (Done, In progress, Next step, Do not redo). Final message: one status line and the handoff path.

### hud

You are teammate `hud` on the claude-team-a agent team; the lead is the main session. Follow the team rules in CLAUDE.md (already in your context).

Task: add the end screen and the HP bar per the "e2: end screen and HP bar" section of game/ARCHITECTURE.md. Write game/src/ui/hud.js with tests in game/test/hud.test.js; update game/index.html and game/src/ui/render.js as that section says.

Teammate `tuner` is changing game/src/core/ and game/src/data/ at the same time: do not edit those. Do not edit game/accept/. There is no browser for you; the lead runs the browser check. Keep DOM code inside functions, never at import time.

Done when: `node --test game/test/hud.test.js game/test/ui.test.js game/test/camera.test.js game/accept/e2-hud.test.js` passes and `node --check` passes for every .js file you changed.

Before your final message, write results/handoff/hud.md (Done, In progress, Next step, Do not redo). Final message: one status line and the handoff path.
