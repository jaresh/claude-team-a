# Benchmarks

A fixed prompt built two ways in a fresh empty repo: by the team (`team_kit.py`, a Sonnet lead
with Haiku teammates) and by one model working alone. Each run is measured (tokens, USD) and
scored three ways, then recorded in `results/`, and the built app is deleted:

1. **Hidden acceptance tests** (`<bench>/accept/`): never shown to the model.
2. **Code-quality metrics** (`quality.py`): size, function length, complexity, duplication,
   docstrings, test/code ratio, and risky patterns (float, SQL from strings, bare except).
   Plus **line coverage** of the app by its own tests (`coverage.py`, counting the CLI and API
   subprocesses the tests start).
3. **A blind review** (`<bench>/review.md`): Opus with read-only tools scores structure,
   readability, correctness risks, error handling, data safety, tests and consistency (1-10)
   and lists the top issues. `.claude/` is removed first, so it can't tell which arm built the
   code. Its cost is recorded apart from the run's.

| Benchmark | What | Hidden tests |
|---|---|---|
| `finance` (v2) | a small-business finance system: ledger, FX, import, budgets, recurring, reports, loans, users and audit, closed periods, invoices, bills, tax, reconciliation, ledger reports, an authenticated HTTP API (Python, stdlib) | 42 |
| `finance/v1` (archived) | the first ten sections only; too small: Sonnet alone built it in 9 turns | 25 |

```
bench/run.sh finance team        # MODEL=sonnet EFFORT=medium by default; KEEP=1 keeps the app
bench/run.sh finance solo
bench/compare.py bench/finance/results/<run> bench/finance/results/<run>
python3 team_kit.py cost --compare <run>/cost.json <run>/cost.json   # cost details
```

Rules for comparable results:

- Don't edit `prompt.md`, `accept/` or `review.md` for a benchmark that has results: the
  version (a hash of the three) is in every result, and `compare.py` warns when versions
  differ. The measuring tools (`quality.py`, `coverage.py`) only add fields. A changed
  benchmark is a new version, with a new reference pair.
- Both arms use the same model, effort and cache. `team` differs only in the kit and the mode
  sentence ("Work with team on it."); `solo` removes the Agent tool, so it really is one model.
- Compare "Total $, cold start" (see `lab/protocol.md`) and hidden tests passed.

Each arm builds in `bench/work/<bench>-<mode>` (git-ignored), a worktree of this repo on an
empty orphan branch, so it is trusted without setup; it is removed after the run.

Reference results: `finance/results/REFERENCE.md` (v2); v1's in `finance/v1/results/`.

## Refresh

Re-run both arms when a model changes (a new Sonnet or Haiku), when the kit changes, and from time
to time: `bench/run.sh finance team` and `bench/run.sh finance solo`, then `bench/compare.py`
against the reference pair. A change is adopted only if it keeps the reference's quality
(hidden tests, review, metrics, coverage) at a lower cost. If the benchmark itself changes
(prompt, hidden tests or review rubric), the version changes, and the first pair on it becomes
the new reference.
