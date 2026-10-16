# claude-team-a

A playable browser roguelike built by agent teams. The game is the test vehicle; the product is
`team_kit.py`, a one-file team kit for Claude Code (see `README.md`).

- Game contracts, layout and commands: `game/ARCHITECTURE.md`
- Experiments: `lab/protocol.md` (design), `lab/run.sh` (start a run), `results/experiments.md`
  (log), `results/runs/<run>/` (specs and results), `results/metrics/` (cost reports)
- The kit is installed here as in any repo (`python3 team_kit.py install .`, git-ignored).
  `team_kit.py` is the source: after editing it, install again to update `.claude/`. A run
  installs the committed version into its own worktree.
