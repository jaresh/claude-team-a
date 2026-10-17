# Run e5: score, stats and high scores (lean lead)

A/B run per `lab/protocol.md`. Base: tag `run/e5/base`, team kit 3.3. Both variants: goal only
(`results/runs/e5/goal.md`, the `/team` skill plans), a Sonnet 5.5 lead at effort medium with
the 1-hour cache (the `lab/run.sh` defaults). The variable is the lead's tool set:

| Variant | Start command | Lead tools |
|---|---|---|
| A | `lab/run.sh --bg results/runs/e5/goal.md A` | default session tools |
| B | `LEAD_ARGS="$(python3 team_kit.py lead --print-args)" lab/run.sh --bg results/runs/e5/goal.md B` (kit 3.4's `team_kit.py` on main) | `team_kit.py lead`: default tools minus the removal list `LEAD_DENY` |

Probes put the start-up prompt at 38.4K tokens (A) and 23.6K (B). B removes only tools a lead
never uses (artifacts and design, feedback and review reports, outside messages, Gmail) and
keeps everything else, including tools the list doesn't know, so it should lose nothing a lead
needs. Kit 3.3 vs 3.4 differ only in `lead`; the skill and agent are the same, so B runs from
the same base as A.

First B attempt (kit 3.3, `--tools` allow-list) never started: `--tools` takes a list of values
and swallowed the prompt that followed it, so the lead sat idle; stopped after a few minutes and
discarded. Fixed in kit 3.4 (`--disallowedTools=...`) and in `lab/run.sh` (lead flags go before
`--settings`). The user then chose a removal list over an allow-list, so new or unknown tools
stay available.

Decided before the run (quality first): B is adopted only if it is accepted on the first check
with no change outside the plan or contract and no failed call to a missing tool, and saves at
least 10% at a cold start.

## Feature

1. **Score and stats**: "e5: score and stats" in `game/ARCHITECTURE.md`.
2. **Run summary and high scores**: "e5: run summary and high scores" in `game/ARCHITECTURE.md`.

Acceptance: `npm test && node --test "game/accept/*.test.js" && node game/tools/smoke.mjs out/e5/<variant>.png --ids inventory,hpbar,end,legend,help,scores`.
The base fails the last two.
