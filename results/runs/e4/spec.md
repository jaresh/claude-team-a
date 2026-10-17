# Run e4, variant A: traps and help overlay (full spec)

A/B run per `lab/protocol.md`. Base: tag `run/e4/base`, team kit 3.0. Both variants: a Sonnet
5.5 lead at effort medium with the 1-hour cache (the `lab/run.sh` defaults), started on the
`/team` skill. The variable is how much the lead is given:

| Variant | Start command | Lead gets |
|---|---|---|
| A | `lab/run.sh --bg results/runs/e4/spec.md A` | this spec: lead steps and teammate prompts word for word |
| B | `lab/run.sh --bg results/runs/e4/goal.md B` | the goal, the contract sections and the check only; the skill plans the rest |
| C | `lab/run.sh --bg results/runs/e4/goal.md C` (branch `run/e4/C`: the base plus kit 3.1) | as B, on kit 3.1 |

B is how the kit is used in a real repo. Compare "Total $, cold start" in the compare file.

## Feature

1. **Traps**: hidden spike, poison and teleport traps that fire when the player steps on them,
   keeping the e2 balance targets. Contract: "e4: traps" in `game/ARCHITECTURE.md`.
2. **Help overlay**: a `?` panel with the keys and a glyph legend that includes revealed traps.
   Contract: "e4: help overlay" in `game/ARCHITECTURE.md`.

## Acceptance (lead runs it once, after the merge)

```
npm test && node --test "game/accept/*.test.js" && node game/tools/smoke.mjs out/e4/A.png --ids inventory,hpbar,end,legend,help
```

All three must pass. The base fails the last two.

## Lead steps

1. In one turn: write `.claude/team/status.md` (one row per teammate) and start `traps` and
   `help` in parallel with the prompts below, word for word: agent type `team-dev`,
   `model: "haiku"`, `effort: "medium"`. Then end the turn.
2. When both have handed back, in one turn: read `.claude/team/changes.md` and the handoffs'
   Done and Next step, then run the acceptance command.
3. If acceptance fails, one fix round: start a successor for the failing part (`traps-2` or
   `help-2`) with the failing output, or fix a one-line problem yourself. Then run the
   acceptance command once more.
4. In one turn: update the status file; copy the team's files with
   `cp -r .claude/team results/runs/e4/A-team`; write `results/runs/e4/A.md` (at most 5 lines:
   acceptance result, fix rounds, successors, anything odd); write `date -u +%FT%TZ` to your
   end-time file (named in your first message); commit everything on the branch and push.
5. Tell the user: "Run done. Type /exit; lab/run.sh will measure it."

## Teammate prompts

### traps

You are teammate `traps` on the claude-team-a agent team; the lead is the main session.

Task: add traps per the "e4: traps" section of game/ARCHITECTURE.md: write game/src/data/traps.js, and change game/src/core/rules.js and game/src/core/game.js, with tests in game/test/traps.test.js. Then check the balance with `node --test game/accept/e2-balance.test.js`; if a target fails, re-tune using only the changes the "e4: traps" and "e2: balance" sections allow. Log each change to a shared table or tuning constant in .claude/team/changes.md.

Teammate `help` is changing game/src/ui/, game/src/main.js and game/index.html at the same time: do not edit those. Do not edit game/sim/ or game/accept/.

Done when: `node --test game/test/traps.test.js game/test/rules.test.js game/test/game.test.js game/test/abilities.test.js game/accept/e4-traps.test.js game/accept/e2-balance.test.js` passes.

Before your final message, write .claude/team/handoff/traps.md. Final message: one status line and the handoff path.

### help

You are teammate `help` on the claude-team-a agent team; the lead is the main session.

Task: add the help overlay per the "e4: help overlay" section of game/ARCHITECTURE.md. Write game/src/ui/help.js with tests in game/test/help.test.js; update game/src/ui/input.js, game/src/main.js, game/index.html, game/src/ui/render.js and game/src/ui/mock-game.js as that section says.

Teammate `traps` is changing game/src/core/ and game/src/data/ at the same time: do not edit those. Do not edit game/accept/. There is no browser for you; the lead runs the browser check. Keep DOM code inside functions, never at import time.

Done when: `node --test game/test/help.test.js game/test/ui.test.js game/test/hud.test.js game/test/legend.test.js game/accept/e4-help.test.js` passes and `node --check` passes for every .js file you changed.

Before your final message, write .claude/team/handoff/help.md. Final message: one status line and the handoff path.
