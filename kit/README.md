# Team kit

Rules, setup and measurement for running a Claude Code agent team: one lead (the main session)
and teammates on Haiku 5.5 at `medium` effort, each kept under ~100K tokens of context.

## Install into another repo

```
python3 kit/install.py /path/to/other/repo
```

It is safe to run again. It:

1. copies `kit/` into the target repo,
2. adds `@kit/rules/team-rules.md` to the target's `CLAUDE.md` (creates the file if missing),
3. sets `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in the target's `.claude/settings.json`, keeping
   everything else in that file,
4. installs the `dev` teammate agent (`kit/agents/dev.md`) into `.claude/agents/`,
5. adds `scratch/`, `out/` and `.claude/settings.local.json` to `.gitignore`,
6. creates `results/` (team status, change log, experiment log, handoff and metrics folders).

Then restart Claude Code in the target repo; the team and the agent load at session start.

## How a run works

1. **Plan** (any session): write `results/runs/<run>/spec.md` with the goal, the contract, one
   prompt per teammate, the acceptance command and the lead steps. Commit it.
2. **Run**: `kit/run.sh results/runs/<run>/spec.md [variant]`. It starts a fresh lead session
   (Sonnet 5.5, effort medium, 5-minute cache; override with `LEAD_MODEL`, `LEAD_EFFORT`,
   `CACHE_TTL`). The lead spawns the teammates, merges, checks acceptance, commits and asks you
   to `/exit`. The script then measures the session, compares it with other variants of the run,
   and commits the report.

Keeping the run's lead session fresh and cheap is the biggest saving: the lead re-reads its whole
context every turn (rules L1-L6).

## What's inside

| Path | What it is |
|---|---|
| `rules/team-rules.md` | The working rules for the lead and teammates. Versions are git tags `rules-vN`. |
| `settings/settings.json` | The settings the installer merges into `.claude/settings.json`. |
| `agents/dev.md` | The teammate agent: Haiku 5.5, medium effort, file and shell tools only. |
| `templates/` | Starting files for `results/`. |
| `run.sh` | Starts a run in a fresh lead session, then measures, compares and commits it. |
| `tools/teamcost.py` | Tokens, peak context and USD cost per agent, read from Claude Code transcripts; `--compare` prints an A/B table. |
| `protocol/experiments.md` | How to measure whether a rules change made the team cheaper. |

## Measure a run

`kit/run.sh` does this for you. By hand:

```
python3 kit/tools/teamcost.py --session <id> --until <end> --json results/metrics/<run>.json
python3 kit/tools/teamcost.py --compare results/metrics/<run>-A.json results/metrics/<run>-B.json
```

`--session` counts one lead session in full with its teammates. Measure a session after it has
ended: its current message isn't complete while it runs. For a time window across sessions use
`--since` / `--until`.

One row per transcript: the lead session and each teammate. It prints numbers only, never message
content. `peak_ctx` is the largest prompt an agent sent; above 100K tokens Haiku 5.5 costs 5x.
