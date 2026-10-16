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
2. **Run** (a fresh session): start Claude Code and say
   `Run results/runs/<run>/spec.md as the lead.` The lead spawns the teammates, merges, checks,
   measures and commits.

Keeping the run's lead session fresh is the biggest saving: the lead re-reads its whole context
every turn (rules L1-L4).

## What's inside

| Path | What it is |
|---|---|
| `rules/team-rules.md` | The working rules for the lead and teammates. Versions are git tags `rules-vN`. |
| `settings/settings.json` | The settings the installer merges into `.claude/settings.json`. |
| `agents/dev.md` | The teammate agent: Haiku 5.5, medium effort, file and shell tools only. |
| `templates/` | Starting files for `results/`. |
| `tools/teamcost.py` | Tokens, peak context and USD cost per agent, read from Claude Code transcripts. |
| `protocol/experiments.md` | How to measure whether a rules change made the team cheaper. |

## Measure a run

```
python3 kit/tools/teamcost.py --latest-session --json results/metrics/<run>.json
```

Run it from the run's lead session: it counts that whole session and its teammates. For a time
window across sessions use `--since` / `--until` instead.

One row per transcript: the lead session and each teammate. It prints numbers only, never message
content. `peak_ctx` is the largest prompt an agent sent; above 100K tokens Haiku 5.5 costs 5x.
