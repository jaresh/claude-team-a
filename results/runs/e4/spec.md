# Run e4: traps and help overlay

A/B run per `kit/protocol/experiments.md`. Base: tag `run/e4/base`. Rules v2.2 and the run lead
of L5 (Sonnet 5.5, effort medium, 1-hour cache) in both variants. The variable is the size of
the lead's start-up prompt:

| Variant | Start command | Lead tools |
|---|---|---|
| A | `kit/run.sh --bg results/runs/e4/spec.md A` | default: every built-in tool, MCP connectors, skills |
| B | `LEAD_ARGS='--tools Agent,Bash,Read,Edit,Write,Glob,Grep,SendMessage,TaskStop --strict-mcp-config --disable-slash-commands' kit/run.sh --bg results/runs/e4/spec.md B` | only the tools a run lead uses; no MCP, no skills |

A Haiku probe measured the start-up prompt at 24.6K tokens (A) and 17.0K (B). The lead re-reads
it on every turn and writes it once, so compare "Total $, cold start" in the compare file: the
plain total depends on whether another session had cached the prefix.

## Feature

1. **Traps**: hidden spike, poison and teleport traps that fire when the player steps on them,
   keeping the e2 balance targets. Contract: "e4: traps" in `game/ARCHITECTURE.md`.
2. **Help overlay**: a `?` panel with the keys and a glyph legend that includes revealed traps.
   Contract: "e4: help overlay" in `game/ARCHITECTURE.md`.

## Acceptance (lead runs it once, after the merge)

```
npm test && node --test "game/accept/*.test.js" && node game/tools/smoke.mjs out/e4/<variant>.png --ids inventory,hpbar,end,legend,help
```

All three must pass. The base fails the last two.

## Lead steps

1. In one turn: update `results/team-status.md` (one row per teammate) and start `traps` and
   `help` in parallel with the prompts below, word for word: agent type `dev`,
   `model: "haiku"`, `effort: "medium"`. Then end the turn (L3).
2. When both have handed back, in one turn: read `results/changes.md` and the handoffs' Done and
   Next step (L4), then run the acceptance command.
3. If acceptance fails, one fix round: start a successor for the failing part (`traps-2` or
   `help-2`, rule 6) with the failing output, or fix a one-line problem yourself. Then run the
   acceptance command once more.
4. In one turn: write `date -u +%FT%TZ` to your end-time file (named in your first message),
   write `results/runs/e4/<variant>.md` (at most 5 lines: acceptance result, fix rounds,
   successors, anything odd), update the status file, commit everything on the branch, push.
5. Tell the user: "Run done. Type /exit; kit/run.sh will measure it."

## Teammate prompts

### traps

You are teammate `traps` on the claude-team-a agent team; the lead is the main session. Follow the team rules in CLAUDE.md (already in your context).

Task: add traps per the "e4: traps" section of game/ARCHITECTURE.md: write game/src/data/traps.js, and change game/src/core/rules.js and game/src/core/game.js, with tests in game/test/traps.test.js. Then check the balance with `node --test game/accept/e2-balance.test.js`; if a target fails, re-tune using only the changes the "e4: traps" and "e2: balance" sections allow. Log each change to a shared table or tuning constant in results/changes.md (rule 13).

Teammate `help` is changing game/src/ui/, game/src/main.js and game/index.html at the same time: do not edit those. Do not edit game/sim/ or game/accept/.

Done when: `node --test game/test/traps.test.js game/test/rules.test.js game/test/game.test.js game/test/abilities.test.js game/accept/e4-traps.test.js game/accept/e2-balance.test.js` passes.

Before your final message, write results/handoff/traps.md (Done, In progress, Next step, Do not redo). Final message: one status line and the handoff path.

### help

You are teammate `help` on the claude-team-a agent team; the lead is the main session. Follow the team rules in CLAUDE.md (already in your context).

Task: add the help overlay per the "e4: help overlay" section of game/ARCHITECTURE.md. Write game/src/ui/help.js with tests in game/test/help.test.js; update game/src/ui/input.js, game/src/main.js, game/index.html, game/src/ui/render.js and game/src/ui/mock-game.js as that section says.

Teammate `traps` is changing game/src/core/ and game/src/data/ at the same time: do not edit those. Do not edit game/accept/. There is no browser for you; the lead runs the browser check. Keep DOM code inside functions, never at import time.

Done when: `node --test game/test/help.test.js game/test/ui.test.js game/test/hud.test.js game/test/legend.test.js game/accept/e4-help.test.js` passes and `node --check` passes for every .js file you changed.

Before your final message, write results/handoff/help.md (Done, In progress, Next step, Do not redo). Final message: one status line and the handoff path.
