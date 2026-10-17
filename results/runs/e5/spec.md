# Run e5: score, stats and high scores (lean lead)

A/B run per `lab/protocol.md`. Base: tag `run/e5/base`, team kit 3.3. Both variants: goal only
(`results/runs/e5/goal.md`, the `/team` skill plans), a Sonnet 5.5 lead at effort medium with
the 1-hour cache (the `lab/run.sh` defaults). The variable is the lead's tool set:

| Variant | Start command | Lead tools |
|---|---|---|
| A | `lab/run.sh --bg results/runs/e5/goal.md A` | default session tools |
| B | `LEAD_ARGS="$(python3 team_kit.py lead --print-args)" lab/run.sh --bg results/runs/e5/goal.md B` | `team_kit.py lead`: only what a lead uses |

Probes put the start-up prompt at 38K tokens (A) and about 21K (B). B keeps skills, MCP (loaded
on demand), web tools and asking the user, so it should lose nothing a lead needs.

Decided before the run (quality first): B is adopted only if it is accepted on the first check
with no change outside the plan or contract and no failed call to a missing tool, and saves at
least 10% at a cold start.

## Feature

1. **Score and stats**: "e5: score and stats" in `game/ARCHITECTURE.md`.
2. **Run summary and high scores**: "e5: run summary and high scores" in `game/ARCHITECTURE.md`.

Acceptance: `npm test && node --test "game/accept/*.test.js" && node game/tools/smoke.mjs out/e5/<variant>.png --ids inventory,hpbar,end,legend,help,scores`.
The base fails the last two.
