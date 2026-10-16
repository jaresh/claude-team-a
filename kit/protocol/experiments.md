# Measuring a rules change

The question each experiment answers: does rules version B build the same feature as version A
for less money, with the same result?

## Design

- **Same feature, same start.** Both variants build one written spec from one base commit. Only
  the rules (or settings) differ. Two different features can't be compared.
- **Same prompts.** The lead reuses the spec and the teammate spawn prompts word for word, saved
  in `results/runs/<run>/`. The lead knows more on the second run; fixed prompts keep that out.
- **Same acceptance check.** A test command, fixed before the first run, decides "accepted".
- **Noise.** One run per variant is noisy. Repeat both when they differ by less than ~20%.

## Steps

1. Lead writes the spec and the acceptance command in `results/runs/<run>/spec.md` and commits.
   Tag the commit `run/<run>/base`.
2. Note the start time (`date -u +%FT%TZ`).
3. Run the team on variant A.
4. Run the acceptance command. Note the end time.
5. `python3 kit/tools/teamcost.py --since <start> --until <end> --json results/metrics/<run>-A.json`
6. Commit the result on branch `run/<run>/A`. Check out the base tag, switch the rules to
   variant B, repeat steps 2-5 on branch `run/<run>/B`.
7. Add one row per variant to `results/experiments.md` and a short note on what changed.

## What to record

| Metric | Source |
|---|---|
| Total, lead and team USD | `teamcost.py` |
| Tool calls, tokens per agent | `teamcost.py` |
| Peak context per teammate, messages over 100K | `teamcost.py` (`peak_ctx`, `over_100k`) |
| Handoffs and successors | `results/handoff/` |
| Accepted on first check | acceptance command |
| Lead fixes after merge | commits by the lead on the run branch |
| Wall time | start and end times |
