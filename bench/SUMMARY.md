# Team kit benchmarks: summary

Status on 2026-10-19. This page compares every benchmark run so far. The detailed records are in
`finance/results/REFERENCE.md` and `warehouse/results/REFERENCE.md`, and the method is in
`README.md`.

## The question

Is it better to have Claude Code build a whole app alone, or to have it lead a team?

- **Solo:** one Sonnet 5.5 session with no subagents.
- **Team:** a Sonnet 5.5 lead with Haiku 5.5 teammates, using `team_kit.py`, the one-file kit
  this repo produces.

Both arms start in a fresh empty repo with the same written spec, model, effort (medium) and
cache. Quality is judged first and cost second.

## Headline

- **Finance benchmark** (42 hidden tests, 4 runs per arm): the team ties solo on quality and
  costs 28-41% less, but takes about twice as long (14 vs 7 minutes).
- **Options on the same benchmark:**
  - "One teammate at a time" gives more consistent code at the same cost, in twice the time.
  - A Haiku lead costs half as much and misses slightly more spec details.
  - An Opus lead shows no measurable gain, at 2.7 times the cost.
- **Warehouse benchmark** (new and harder, 62 hidden tests, 2 runs per arm so far): scores now
  spread out. The team is level or ahead on quality in both runs. Its cost varies: one team run
  cost about as much as solo, the other 37% less.

## How a run is measured

1. **Hidden acceptance tests.** They are never shown to the model. They are trusted only after
   they pass against a reference implementation written for the benchmark.
2. **Code metrics.** Size, function length, complexity, duplication and risky patterns, plus the
   line coverage of the app's own tests.
3. **A blind review.**
   - Opus scores seven areas from 1 to 10 and lists the top issues: structure, readability,
     correctness risks, error handling, data safety, tests and consistency.
   - It reads a copy of the code with no git history, kit files or README, so it can't tell
     which arm wrote the code.
   - Since the lead-model test, a Sonnet reviewer gives a second opinion.
4. **Cost.** Tokens and USD are replayed from the session transcripts and priced at a cold
   start. Review cost is recorded separately and isn't counted.

**Rules for a result to count:**

- Reviewer noise floor: three reviews of the same code differ by up to 1 point, so a 1-point
  difference is a tie.
- At least 3, and in practice 4, runs per arm, compared on medians.
- A result counts only if the winner stays the same when any one run is left out
  (leave-one-out; `spread.py`).
- A cost difference under 10% is treated as a tie.

One run proves nothing. Two solo runs of the same prompt got reviews of 8 and 6 and cost $1.62
and $1.06.

## Finance benchmark (v2.1, 42 hidden tests)

The app is a small-business finance system: ledger, FX, import, budgets, recurring entries,
invoices, bills, tax, reconciliation, users and audit, reports and an HTTP API (Python standard
library only). Figures are the median with the range in brackets, over 4 runs unless the table
says otherwise.

| Arm | Hidden tests | Review | Consistency | Cost $, cold | Minutes | Teammates |
|---|---|---|---|---|---|---|
| Solo Sonnet | 42 (42-42) | 7 (6-7) | 7 (7-8) | 1.154 (1.098-1.319) | 7 | - |
| Team, Sonnet lead, kit 3.10 | 42 (41-42) | 6.5 (5-7) | - | **0.676** (0.604-0.774) | 13 | 5 |
| Team, Sonnet lead, kit 3.11 | 42 (41-42) | 7 (7-7) | 6 (6-7) | 0.832 (0.654-0.866) | 14 | 6.5 |
| Team, one teammate at a time | 41 (41-42) | 7.5 (7-8) | **8** (7-8) | 0.773 (0.722-0.921) | 28 | 6.5 |
| Team, Haiku lead | 41 (41-42) | 7 (7-8) | 6 (6-7) | **0.416** (0.334-0.468) | 31 | 12.5 |
| Team, Opus lead | 42 (42-42) | 8 (7-8)* | 7.5 (7-8) | 2.238 (2.038-2.472) | 14 | 4 |
| Solo Haiku (1 run) | 42/42 | 7 | 8 | 0.312 | 36 | - |

\* The Opus reviewer gave the Opus-led code 8 in three of four runs; the Sonnet reviewer gave it
7 every time. That looks partly like a preference for its own model family, so under the method
it is a tie.

What finance taught us:

- **Quality is a tie.**
  - The team's rare hidden-test misses were spec details that cross a task boundary, such as a
    repeated flag, closed periods in imports, or an API response shape.
  - The clearest one disappeared when the spec's wording was fixed (v2 to v2.1).
- **Cost comes mainly from the lead.**
  - Each lead turn re-reads its whole context. A teammate on Haiku costs $0.02-0.03.
  - So the number of lead turns and teammates the lead chooses causes most of the cost spread.
- **Consistency across modules is the team's weak score.**
  - Teammates working in parallel name and repeat helpers in different ways: 6, against solo's 7.
  - Running one teammate at a time raises it to 8.
- **Kit changes that worked:**
  - 3.10 dropped the consistency pass, which was 24% cheaper at the same quality.
  - 3.11 added a rule against test helpers named like test-framework methods. A lead's `fail`
    helper had made assertions pass silently in 2 of 4 runs; with the rule it happened in 0 of 4.
  - 3.13 forces every teammate onto Haiku and has teammates compact at 100K.
- **Tried and dropped** (`../ARCHIVE.md`):
  - A consistency pass after the last wave.
  - A Haiku auditor after the last wave: it found issues, but fixing them cost more and the
    review didn't move.
  - A Haiku advisor for teammates: it was never called.
- **Validity fixes along the way:**
  - Solo sessions could leave the bench workspace through `EnterWorktree`, and once pushed a
    branch. Worktree tools and `git push` are now denied, and the affected runs were checked or
    discarded.
  - The review is now fully blind.

**Conclusion on finance:** a Sonnet lead with Haiku teammates gives solo-level quality at lower
cost. Finance is near its ceiling, though: almost every arm reaches 42/42 and a review of 7, so
it can't separate the arms on quality. That is why the warehouse benchmark was built.

## Warehouse benchmark (new, 62 hidden tests in three tiers)

The app is inventory and orders: FIFO and average costing, lots and serials, reservations that
expire, purchase orders, transfers in transit, returns at cost, voids, as-of reports,
promotions, and an HTTP API with ETags, idempotency keys and concurrent requests. The spec is
about 4,200 words.

The hidden tests come in three tiers:

- **T1** tests one feature (31 tests).
- **T2** tests features combined (21).
- **T3** tests robustness: atomicity, permissions, HTTP and concurrency (10).

A reference implementation passes all 62. Both arms use kit 3.13, with two runs per arm so far.

| Run | Hidden (T1 / T2 / T3) | Review: Opus / Sonnet | Readability, Opus | Cost $, cold | Minutes | Turns | Own tests |
|---|---|---|---|---|---|---|---|
| Solo 1 | 59 (30 / 21 / 8) | 7 / 6 | 5 | 1.513 | 10 | 13 | 14, 82% coverage |
| Solo 2 | **62** (31 / 21 / 10) | 6 / 6 | 6 | 1.679 | 10 | 18 | 11, 85% coverage |
| Team 1 | 61 (30 / 21 / 10) | 7 / 7 | 7 | 1.582 | 30 | 28 | 108, 93% coverage |
| Team 2 | 61 (30 / 21 / 10) | 7 / 7 | 8 | **1.002** | 50 | 19 | 129, 92% coverage |
| **Solo, median** | 60.5 | 6.5 / 6 | 5.5 | 1.596 | 10 | 15.5 | |
| **Team, median** | 61 | 7 / 7 | 7.5 | 1.292 | 40 | 23.5 | |

Early reading, which is not yet a result (that needs 4 runs per arm):

- **The scores spread now.**
  - Reviews land at 6-7, with sub-scores from 4 to 9.
  - The hidden tests catch real misses:
    - Solo 1 let the read-only `viewer` role write stock.
    - Both team runs returned a receipt's serial numbers unsorted, while solo sorted them both
      times. The spec asks for this only through its general rule ("where nothing is stated,
      … ascending").
    - The team's miss looks like finance's misses: a spec-wide rule that doesn't reach the
      teammate writing that one command. It's the next thing to look at in the kit.
- **Tests and reviews catch different defects.**
  - Solo 2 passed every hidden test, yet both reviewers scored it 6.
  - They found a crash with a traceback when a voided scrap brings back a serial that is
    already in stock.
  - They also found short names, star imports, and the CLI and HTTP layers tangled together.
- **The team's code is better structured.**
  - Review structure was 7 in both team runs and 6 in both solo runs, and the difference holds
    when either run is left out.
  - The team had 8 and 6 functions above complexity 10, against 14 and 12 for solo.
  - It wrote 1,200-1,300 test lines, against about 280.
  - Coverage of its own tests was 92-93%, against 82-85%.
- **Cost depends on the lead's turns, as on finance.**
  - Team 1: the lead took 28 turns ($1.33), and the run cost $1.58, as much as solo.
  - Team 2: the lead took 19 turns ($0.72), and the run cost $1.00, 37% below the solo median.
  - Teammates cost $0.26-0.28 in both runs. Solo writes the whole app in 13-18 large turns.
- **Wall time:** the team takes 3-5 times as long, 30 and 50 minutes against 10.
- **Leave-one-out with 2 runs per arm:** structure, coverage and cost favour the team and hold;
  hidden tests and review overall flip. Two runs is below the method's minimum.

## Current recommendation

- **Default:** a Sonnet lead with Haiku teammates (kit 3.13) and tasks in parallel. It ties solo
  on quality, and on a mid-size spec it is cheaper.
- **When code consistency matters and waiting is fine:** add "one teammate at a time" to the
  prompt.
- **On a tight budget:** a Haiku lead, at half the cost, slower, with slightly more spec misses.
- **Not worth it on a well-specified task:** an Opus lead.

**Open questions:**

- Does the team's cost advantage survive bigger specs? On warehouse, one team run cost as much
  as solo and one 37% less; 4 runs per arm will settle it.
- Haiku lead and solo Haiku need their own 4-run checks: a second solo Haiku run with an
  advisor failed completely, with 0/42 hidden tests.
- Still untested:
  - The workflow variant, which needs dynamic workflows enabled.
  - A benchmark on an existing codebase rather than an empty repo.

## Where to look

| Path | What |
|---|---|
| `README.md` | how runs are started, scored and compared; the method |
| `finance/results/REFERENCE.md` | every finance run and experiment, in order |
| `warehouse/results/REFERENCE.md` | warehouse runs |
| `<bench>/results/<run>/` | one run: `summary.json`, hidden test log, reviews, cost |
| `spread.py <bench>/results` | medians, ranges and the leave-one-out check |
| `../team_kit.py` | the kit itself; `../README.md` explains how to install and use it |
| `../ARCHIVE.md` | retired kit features and why |
