# Measuring a workflow change

The question each experiment answers: does variant B (a rules change, a lead setting, an agent
definition) build the same feature as variant A for less money, with the same result?

## Design

- **Same feature, same start.** Both variants build one written spec from one base commit. Only
  the variable under test differs. Two different features can't be compared.
- **Same prompts.** The spec holds the teammate prompts word for word; both leads use them.
- **Same acceptance check.** A command fixed in the spec, before the first run, decides
  "accepted".
- **Fresh sessions.** Each variant runs in its own fresh lead session (`kit/run.sh`), so neither
  pays for the other's context, and each is measured as one whole session.
- **Noise.** One run per variant is noisy. Repeat both when they differ by less than ~20%.

## Steps

1. **Plan** (planning session): write `results/runs/<run>/spec.md` (goal, contract, teammate
   prompts, acceptance command, lead steps, and how each variant is started), plus the
   acceptance tests. Commit it on main and tag the commit `run/<run>/base`.
2. **Variant A**: `kit/run.sh results/runs/<run>/spec.md A`, with the variant's settings in the
   environment if the spec says so (for example `LEAD_MODEL=opus`). The lead runs the team,
   checks acceptance, writes its end time, commits, pushes and asks you to `/exit`.
3. `kit/run.sh` then measures the session up to the end time
   (`results/metrics/<run>-A.json`), commits the report and pushes.
4. **Variant B**: the same with `B`. After the session, `kit/run.sh` also writes
   `results/runs/<run>/compare-A-B.md` from both reports.
5. **Decide** (planning session): add one row per variant to `results/experiments.md` and a
   short verdict; merge the winning branch into main.

To measure by hand: `teamcost.py --session <id> --until <end>` for one session, or
`--since/--until` for a time window across sessions (a long session, rules v0). Don't measure a
session from inside itself: its current message isn't complete yet.

## What to record

| Metric | Source |
|---|---|
| Total, lead and team USD; lead cache read, cache write and output | `teamcost.py --compare` |
| Tool calls, tokens, peak context per agent; messages over 100K | `teamcost.py` |
| Handoffs and successors | `results/handoff/` |
| Accepted on first check; fixes by the lead | `results/runs/<run>/<variant>.md` |
| Wall time | the session's first message to the end time |
