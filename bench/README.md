# Benchmarks

A fixed prompt built two ways in a fresh empty repo: by the team (`team_kit.py`, a Sonnet lead
with Haiku teammates) and by one model working alone. Each run is scored with hidden acceptance
tests, measured, recorded in `results/`, and the built app is deleted.

| Benchmark | What | Hidden tests |
|---|---|---|
| `finance` | a finance system: ledger, FX, CSV import, budgets, recurring, reports, loans, HTTP API (Python, stdlib) | 25 |

```
bench/run.sh finance team        # MODEL=sonnet EFFORT=medium by default; KEEP=1 keeps the app
bench/run.sh finance solo
bench/compare.py bench/finance/results/<run> bench/finance/results/<run>
python3 team_kit.py cost --compare <run>/cost.json <run>/cost.json   # cost details
```

Rules for comparable results:

- Don't edit `prompt.md` or `accept/` for a benchmark that has results: the prompt version (a
  hash of both) is in every result, and `compare.py` warns when versions differ. A changed
  benchmark is a new version, with a new reference pair.
- Both arms use the same model, effort and cache. `team` differs only in the kit and the mode
  sentence ("Work with team on it."); `solo` removes the Agent tool, so it really is one model.
- Compare "Total $, cold start" (see `lab/protocol.md`) and hidden tests passed.

Reference results: see `results/REFERENCE.md` once the first pair is in.
