# claude-team-a

A one-file team kit for Claude Code, `team_kit.py`, and the testbed that tunes it: a browser
roguelike (`game/`) built by agent teams, with every run's cost measured (`results/`).

## The kit

The session you start is the lead. Type `/team <task>` (or ask for "the team") and it:

1. plans the task in `.claude/team/plan.md`: goal, check command, contract, and bounded tasks
   with no file in two tasks;
2. runs the tasks in parallel on `team-dev` teammates (Haiku 5.5, effort medium, about 100K
   tokens of context each), which write handoffs;
3. merges, runs the check once, and reports. It doesn't commit unless you ask.

A spec file in the prompt (`/team follow docs/spec.md`) replaces the planning step.

**Parallel or one at a time: you choose in the prompt.** "Work with team on it." runs the
tasks in parallel. "Work with team on it, one teammate at a time." runs them one after another,
each building on the code before it. On the finance benchmark (4 runs each, kit 3.11) one at a
time gave more consistent code (review consistency 8 vs 6, overall 7.5 vs 7) at about the same
cost ($0.77 vs $0.83), but took twice as long (28 vs 14 minutes) and missed one more spec detail
(hidden tests 41 vs 42). Use it when code quality matters more than waiting.

Recommended start: `python3 .claude/skills/team/team_kit.py lead "<task>"` (`-- --model sonnet`
and other claude flags after `--`). It opens the same session without the tools a lead never
uses (artifacts, feedback reports, outside messages, Gmail), so the start-up prompt the lead
re-reads every turn drops from about 40K to 25K tokens: 22% cheaper per team run in e5, with
the same result. `--deny NAMES` removes more for one session.

```
python3 team_kit.py install /path/to/repo     # or run it from inside the repo
python3 team_kit.py status /path/to/repo
python3 team_kit.py uninstall /path/to/repo   # --keep-work keeps .claude/team/
python3 .claude/skills/team/team_kit.py lead "<task>"   # lean lead session on /team <task>
python3 .claude/skills/team/team_kit.py cost  # tokens and USD of the latest session (cost --help)
```

The script is all you need: copy or download it, run `install`. It writes only these files,
hides them from git through `.git/info/exclude`, and leaves tracked files, `.gitignore` and
`CLAUDE.md` alone; `uninstall` restores the repo byte for byte:

| Path | What |
|---|---|
| `.claude/skills/team/SKILL.md` | the lead's playbook, loaded only when the team is asked for |
| `.claude/skills/team/team_kit.py` | a copy of the script (request, cost, status, uninstall) |
| `.claude/agents/team-dev.md` | the teammate, with its rules (scope, budget, handoff) |
| `.claude/settings.local.json` | merged in: agent teams on, Haiku auto-compact at 100K |
| `.claude/team/` | working files: plan, status, change log, handoffs, scratch |

Restart sessions that were open during the install. Cost tips from the experiments: start a big
team task in a fresh session (the lead re-reads its whole context every turn, and it is most of
the cost), and a Sonnet lead costs far less than Opus for a well-defined task.

## The testbed

| Path | What |
|---|---|
| `game/` | the roguelike; contracts and commands in `game/ARCHITECTURE.md` |
| `lab/run.sh` | starts one experiment run in a fresh lead session, then measures and commits it |
| `lab/protocol.md` | how an A/B experiment is designed and compared |
| `results/experiments.md` | every run: cost, result, verdict |
| `results/runs/<run>/` | specs, per-variant results, comparisons |
| `results/metrics/` | cost reports (JSON) |

Run: `python3 team_kit.py install .` once, then `lab/run.sh --bg results/runs/<run>/spec.md A`.
