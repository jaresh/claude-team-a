# Benchmarks

Results so far, in one page: `SUMMARY.md`.

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
   and lists the top issues. It reads a copy in a new temporary folder (`review-XXXXXX/app`)
   without `.git`, `.claude/` or Markdown files, so neither the path, the branch nor the app's
   README shows which arm built the code. Its cost is recorded apart from the run's.

| Benchmark | What | Hidden tests |
|---|---|---|
| `finance` (v2.1) | a small-business finance system: ledger, FX, import, budgets, recurring, reports, loans, users and audit, closed periods, invoices, bills, tax, reconciliation, ledger reports, an authenticated HTTP API (Python, stdlib) | 42 |
| `warehouse` | inventory and orders: FIFO and average costing, lots and serials, reservations that expire, purchase orders with an over-receipt limit, transfers in transit, returns at cost, voids, as-of reports, promotions, an HTTP API with ETags, idempotency keys and concurrent requests (Python, stdlib). Built to be hard enough that scores spread | 62 in three tiers: T1 one feature (31), T2 features combined (21), T3 robustness (10) |
| `change` | **changes to an existing repo**: starts from `change/base/` (the warehouse app as a package of 13 modules, about 1.9K lines, with docs and a smoke test) instead of an empty repo. Three tasks: fix a reported bug (`--at` leaves out a movement made exactly at that time; two reports, one cause), archive products (8 commands, the HTTP API, audit, reorder) and customer credit limits (customers, sales orders, audit). Built to measure navigation cost: how much the agents read to find their way. The first version (one module, two tasks) was too small: the lead did it alone for $0.44, and its two runs are in `change/results/v1-small/` | 23 new in three tiers (T1 the bug 3, T2 archive and credit limit 13, T3 archive across commands and HTTP 7) plus the 62 warehouse tests as a regression suite |
| `finance/v1` (archived) | the first ten sections only; too small: Sonnet alone built it in 9 turns | 25 |

```
bench/run.sh finance team        # MODEL=sonnet EFFORT=medium by default; KEEP=1 keeps the app
bench/run.sh finance solo
bench/compare.py bench/finance/results/<run> bench/finance/results/<run>
bench/spread.py bench/finance/results            # medians, ranges, noise floor, stability
REVIEWS=3 bench/run.sh finance solo              # three independent reviews of one build
python3 team_kit.py cost --compare <run>/cost.json <run>/cost.json   # cost details
```

`change/reference/` is `base` with the bug fixed and the feature added; it passes all 85 (`APP_DIR=bench/change/reference python3 -m unittest discover -s bench/change/accept`), and `base` fails exactly the 21 new ones that can fail (2 of the 23 pass by accident). `run.sh` copies `base/` into the workspace as its first commit when the benchmark has one.

Hidden tests are only trusted once they pass against a reference implementation:
`warehouse/reference/` (never shown to the arms) passes all 62:
`APP_DIR=bench/warehouse/reference python3 -m unittest discover -s bench/warehouse/accept`.
Runs record `accept_tiers` (passed and total per tier), and `spread.py` prints a row per tier.

Rules for comparable results:

- Don't edit `prompt.md`, `accept/` or `review.md` for a benchmark that has results: the
  version (a hash of the three) is in every result, and `compare.py` warns when versions
  differ. The measuring tools (`quality.py`, `coverage.py`) only add fields. A changed
  benchmark is a new version, with a new reference pair.
- Both arms use the same model, effort and cache. `team` differs only in the kit and the mode
  sentence ("Work with team on it."); `solo` removes the Agent tool, so it really is one model.
- Compare "Total $, cold start" (see `lab/protocol.md`) and hidden tests passed.

## Method: how many runs, and when a result counts

One run per arm can't rank anything: on finance v2, two solo runs on the same prompt scored a
review of 8 and 6 and cost $1.62 and $1.06. So:

1. **Reviewer noise floor.** `REVIEWS=3` reviews the same code three times, in parallel. The
   widest spread of one run's reviews is the floor: a review difference no larger than it is a
   tie. Measure it on one run of each arm per prompt version, and again when the reviewer
   model changes.
2. **At least 3 runs per arm** (team on one kit version; solo), on the same prompt version.
   Report the median and range: `bench/spread.py bench/<bench>/results`.
3. **Stability.** For each metric, `spread.py` says which arm is better on the medians, and
   whether that still holds when any one run of either arm is left out. The decision metrics
   are hidden tests passed, review overall and cost at a cold start.
4. **Stopping rule.** The method is proven, and a comparison is settled, when all three
   decision metrics are stable. If one flips, add one run to each arm and check again, up to 5
   per arm. A metric still flipping at 5 is a difference the benchmark can't resolve: report it
   as a tie within noise.

A kit change is judged the same way: 3 runs of the new kit against the current kit's runs.

**Single-change variants** (`bench/variants/`): each file there is one change to `team_kit.py`
(`apply(src)`), tested before it goes into the kit: `VARIANT=done-gate bench/run.sh finance
team` installs that variant, and its results carry the kit version `3.13+done-gate`. Adopted
variants move into `team_kit.py`; retired ones are listed in `ARCHIVE.md`. Other
arms: `MODEL=haiku` (solo or lead on Haiku), `CLAUDE_ARGS="--advisor sonnet"`, `ARM=<name>`.
One run each first; a variant that holds gets the full 4 runs before it is adopted.

First check of the method (finance v2, kit 3.9 against solo): the reviewer's noise floor was 0
for the overall score and 1 for sub-scores, and all three decision metrics were stable at 4 runs
per arm (review flipped at 3). Plan on 4 runs per arm. See `finance/results/REFERENCE.md`.

Each arm builds in `bench/work/<bench>-<mode>` (git-ignored), a worktree of this repo on an
empty orphan branch, so it is trusted without setup; it is removed after the run.

Reference results: `finance/results/REFERENCE.md` (v2.1 at the end, v2 before it); v1's in
`finance/v1/results/`. Both arms run without the worktree tools and without `git push`.

## Refresh

Re-run both arms when a model changes (a new Sonnet or Haiku), when the kit changes, and from time
to time: `bench/run.sh finance team` and `bench/run.sh finance solo`, then `bench/compare.py`
against the reference pair. A change is adopted only if it keeps the reference's quality
(hidden tests, review, metrics, coverage) at a lower cost. If the benchmark itself changes
(prompt, hidden tests or review rubric), the version changes, and the first pair on it becomes
the new reference.
