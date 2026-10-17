# Finance benchmark v2: reference results (version 141f43ad9356)

First pair, 2026-10-17: `bench/finance/prompt.md` (v2: seventeen sections) built by the team
(kit 3.6, `team_kit.py lead` flags; Sonnet 5.5 lead, Haiku 5.5 teammates) and by Sonnet 5.5
alone (no subagents), both at effort medium with the 1-hour cache. Scored with the 42 hidden
tests, `bench/quality.py` and a blind Opus review (`review.md`). Coverage was added after this
pair, so it starts with the next runs. Compare later runs with
`bench/compare.py bench/finance/results/20261017T092229Z-solo bench/finance/results/20261017T092204Z-team <new run>`.

| Metric |  |  |
|---|---|---|
| Run | 20261017T092229Z-solo | 20261017T092204Z-team |
| Mode | solo | team |
| Model / effort | sonnet / medium | sonnet / medium |
| Prompt version | 141f43ad9356 | 141f43ad9356 |
| Hidden tests passed | 42/42 | 41/42 |
| Own tests passed | 66/66 | 139/139 |
| Own tests' line coverage | - | - |
| Python lines | 2508 | 3068 |
| Total $ | 1.583 | 0.673 |
| Total $, cold start | 1.620 | 0.715 |
| Lead / solo $ | 1.583 | 0.510 |
| Team $ | 0.000 | 0.163 |
| Teammates | 0 | 5 |
| Lead / solo messages | 26 | 12 |
| Lead / solo peak context | 112K | 58K |
| Lead / solo compactions | 0 | 0 |
| Team peak context | 0K | 64K |
| Wall time | 09:22-09:32 | 09:22-09:34 |
| **Review overall** (1-10) | 8 | 7 |
| Review: structure | 8 | 7 |
| Review: readability | 7 | 7 |
| Review: correctness_risks | 7 | 6 |
| Review: error_handling | 7 | 6 |
| Review: data_safety | 9 | 8 |
| Review: tests | 7 | 7 |
| Review: consistency | 8 | 6 |
| Metric: app_lines | 1281 | 1347 |
| Metric: test_to_app_ratio | 0.62 | 0.83 |
| Metric: mean_function_lines | 8.6 | 7.2 |
| Metric: functions_over_50_lines | 1 | 0 |
| Metric: max_complexity | 16 | 22 |
| Metric: functions_complexity_over_10 | 4 | 4 |
| Metric: duplicate_share | 0.0 | 0.0 |
| Metric: docstring_coverage | 0.19 | 0.24 |
| Metric: float_calls | 0 | 0 |
| Metric: sql_built_from_strings | 6 | 9 |
| Metric: bare_except | 0 | 0 |
| Review cost $ (not in total) | 0.8804 | 0.5524 |

**Cost: the team is 56% cheaper at a cold start** ($0.715 vs $1.620; v1: 25%). Solo needed 26
turns and grew to a 112K-token context; the team lead needed 12 turns and peaked at 58K, and
five Haiku teammates (`books`, `data`, `api`, `reports`, `invoices`) wrote most of the code for
$0.163. No teammate came near its budget (peak 64K), so there were no successors; `reports`
again left no handoff file (four of five did), probably the same Claude Code guard against
subagent "report files" that hit `summary` in e5.

**Quality: the team is a little lower.** Hidden tests 41/42 vs 42/42; review 7 vs 8.

- The failed test: repeated `--clear 1 --clear 2` kept only the last id (an argparse
  `nargs="*"` store). The spec's `[--clear ID ...]` allows reading it as one list, but a
  correct implementation accepts both, as solo's did. The spec stays as is, for comparability.
- The review's main team findings: naming and helper patterns differ between modules written by
  different teammates (consistency 6 vs 8); posting validation and amount parsing are
  implemented twice, in different forms; reports round per account before adding up, so
  converted totals can be a cent off; the API runs requests through the CLI's argument parser.
- The team wrote more tests (139 vs 66; test/code ratio 0.83 vs 0.62) and shorter functions.

**What to optimize next (the sweet spot):** the gap is cross-module consistency, which the lead's
contract can fix: name one shared module for validation, amount parsing and rounding, and the
conventions (naming, argument style) every teammate follows, and have teammates reuse rather
than re-implement. Plus a handoff file name the subagent guard doesn't block. The goal is the
team's cost with solo's review score.

## Later runs (same prompt version, team arm)

| Run | Kit | Hidden | Review (consistency) | Cold $ | Lead msgs | Teammates | Consistency pass |
|---|---|---|---|---|---|---|---|
| 20261017T092204Z-team (reference) | 3.6 | 41/42 | 7 (6) | 0.715 | 12 | 5 | - |
| 20261017T094531Z-team | 3.7 | 42/42 | 8 (7) | 0.732 | 14 | 5 | skipped |
| 20261017T095916Z-team | 3.8 | 41/42 | 7 (6) | 0.957 | 19 | 7 | skipped, said so in README |
| 20261017T101624Z-team | 3.9 | 40/42 | 6 (6), tests 4 | 1.039 | 23 | 8 | ran |

- **3.7** (shared Conventions, `.txt` handoffs, team size left to the lead): solo's hidden-test
  and review scores at the team's cost. Every handoff was written. The lead skipped the
  consistency pass, so posting rules still live in three places.
- **3.8** (the consistency pass as its own required step 4): the lead skipped it anyway. It
  started seven teammates whose plan pointed at `.claude/team/spec.md` before writing that file,
  then spent eight messages sending it to them (lead $0.75 vs $0.56). It put the HTTP server in
  the same wave as invoices, so the server's tests never ran real invoice commands, and the
  hidden API invoice test failed (`number` missing). It finished while one teammate was still
  re-checking, never updated `status.md`, and committed although not asked.
- **3.9** responds: the plan gets its `consistency` section at planning time and `status.md`
  a `waiting` row for it; Finish waits for every row; the spec is saved before the first wave;
  a layer over other tasks' code (an API, a UI) goes in a later wave; acceptance tests cover
  interfaces between tasks; no commit, even at the end.
- **3.9 result:** the lead followed every new rule: spec saved first, the API in its own later
  wave, the consistency teammate run, Finish after it, nothing committed. Quality still fell:
  40/42 (closed periods for import and recurring; clearing across statements) and review 6. The
  review's worst finding is in the lead's own test helper: `BookTest.fail` overrides
  `unittest.TestCase.fail`, so most list and dict assertions can never fail (tests 4). The
  consistency teammate moved small helpers into core (dates, totals, tax rates) but, held to
  "change no behaviour", left the bill and invoice copies apart, so consistency stayed 6. Cost
  rose to $1.039: eight teammates, 23 lead messages, the lead writing the core itself.
- **Reading the four team runs together:** the run-to-run spread (review 6 to 8, cold cost
  $0.72 to $1.04) is as large as any difference between kit versions, so one run per version
  can't rank them. 3.7's result may have been a good draw. Every team run so far is 36-56%
  cheaper than the single solo run.
