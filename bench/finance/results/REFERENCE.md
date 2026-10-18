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

## Second solo run (20261017T114048Z-solo)

| Solo run | Hidden | Review (consistency, tests) | Cold $ | Messages | Own tests | Lines |
|---|---|---|---|---|---|---|
| 20261017T092229Z-solo (reference) | 42/42 | 8 (8, 7) | 1.620 | 26 | 66 | 2508 |
| 20261017T114048Z-solo | 42/42 | 6 (7, 5) | 1.061 | 10 | 26 | 1955 |

- Solo varies as much as the team: the second run wrote the app in 10 messages (59K output
  tokens), with less code and far fewer tests. Its review found tautological test assertions
  (`X if False else Y`, test_core.py and test_business.py) and a ~900-line `Book` class holding
  every feature, with bill and invoice code duplicated.
- **Across both arms the review is a tie within the spread** (solo 8 and 6; team 8, 7 and 6).
- **Hidden tests are the one consistent gap:** solo 42/42 twice, the team 42, 41 and 40. The
  team's misses are spec details that cross a task boundary: a repeated flag, closed periods in
  import and recurring runs, clearing across statements, an API response shape.
- **Cost:** the team is still cheaper (team $0.73-1.04 vs solo $1.06-1.62), but against the
  cheaper solo run the margin ranges from 31% (kit 3.7) to 2% (kit 3.9). From 3.7 to 3.9 the
  lead's messages grew from 14 to 23 (more waves: a separate API wave and the consistency
  pass), and the lead's cost from $0.56 to $0.76.

## Method check: kit 3.9 against solo, 4 runs each

The method in `bench/README.md` (noise floor, 3+ runs per arm, leave-one-out stability,
stopping rule), run on the current kit. `bench/spread.py bench/finance/results` prints it.

| Decision metric | Team, kit 3.9 (n=4) | Solo (n=4) | Better | Leave-one-out |
|---|---|---|---|---|
| Hidden tests passed | 41 (40-42) | 42 (42-42) | solo | stable |
| Review overall | 7 (6-7) | 7 (6-8) | tie | stable |
| Cost $, cold start | 1.030 (0.984-1.077) | 1.119 (1.056-1.620) | team | stable |

- **Reviewer noise floor:** three reviews of the same build gave the same overall score (7, 7,
  7, for one build of each arm); sub-scores moved by at most 1. So one review per run is
  enough, and a sub-score difference of 1 is a tie.
- **Runs needed:** at 3 per arm, hidden tests and cost were stable but the review flipped; at 4
  per arm all three decision metrics are stable, so the stopping rule ended there.
- **Spread:** the team's cost is tight (±5%); solo's has one outlier ($1.62, 26 turns; the
  other three $1.06-1.18). Solo passed all 42 hidden tests in every run.
- **The hidden-test gap is one test:** `TestReconcile.test_clearing_across_statements` failed
  in three of the four kit 3.9 runs (and in 3.6's), and the only other team miss was once. It
  passes `--clear` twice; the spec writes `[--clear ID ...]`, and the team's code takes one
  list. Solo accepted both forms every time.
- **Correction to earlier figures:** the 55-56% saving quoted for kits 3.6 and 3.7 compared
  one team run with solo's outlier. Against solo's median ($1.12), kit 3.9 saves 8%; 3.7's
  single run ($0.73) would be 35%, but it needs its own 3-4 runs before that counts.
- **Minimum effect (recommended):** an 8% saving is stable here but small next to the spread
  of a single run. Requiring at least 10% for a cost win would make this cost result a tie.

## Kit 3.10 (request command, no consistency pass), 4 runs

| Decision metric | Kit 3.10 (n=4) | Kit 3.9 (n=4) | Solo (n=4) |
|---|---|---|---|
| Hidden tests passed | 41 (40-42) | 41 (40-42) | 42 (42-42) |
| Review overall | 7 (7-7), n=3 | 7 (6-7) | 7 (6-8) |
| Cost $, cold start | 0.785 (0.560-0.839) | 1.030 (0.984-1.077) | 1.119 (1.056-1.620) |

- Same quality as 3.9 at 24% lower cost; 30% below solo's median. Against solo: hidden tests
  solo (stable), review tie (stable), cost team (stable).
- Run 20261017T160444Z-team has no review (the review session failed, probably the usage
  limit); its code is deleted, so the review median uses 3 runs.
- Adopted: kit 3.10 is the current kit.

# Finance v2.1 (prompt 87a9b86a9023): the reference

v2.1 = v2 with a fully blind review (the reviewer reads a copy in a new temporary folder, without
`.git`, `.claude/` or Markdown files) and `--clear` written like `--posting` (one flag per id).
Since 2ec0a25 both arms also lose the worktree tools and `git push` (see below).

| Decision metric | Team, kit 3.10 (n=4) | Solo (n=4) | Better | Leave-one-out |
|---|---|---|---|---|
| Hidden tests passed | 42 (41-42) | 42 (42-42) | tie | stable |
| Review overall | 6.5 (5-7) | 7 (6-7) | tie (floor 1) | stable |
| Cost $, cold start | **0.676** (0.604-0.774) | 1.154 (1.098-1.319) | team, -41% | stable |

- The method held: all three decision metrics stable at 4 runs per arm. The blind review's
  noise floor is 1 for every score (one solo build got 6, 7 and 7).
- The `--clear` test now passes in every team run: the v2 gap was the spec's wording.
- Own tests: the team's cover more (96% vs 94%), but the review scores them lower (5.5 vs 6.5,
  not stable). In run 20261017T194134Z-team (review 5) the test helper `Book.fail` overrides
  `unittest.TestCase.fail`, so failing assertions pass silently: the same bug as in kit 3.9's
  20261017T101624Z-team. A recurring lead mistake, and the next thing to fix in the kit.
- Wall time: the team takes longer (13 vs 7 minutes).

**Validity.** Solo sessions called `EnterWorktree` as their first action, which makes a worktree
of this whole repo. In 20261017T092229Z, 133556Z, 192701Z and 193756Z (all solo) the session
ran `pwd`, `ls` and `git log` there, removed it within seconds and built in the bench workspace:
no hidden-test or result file was read, so those runs stand. A solo run at 19:47 built in the
worktree and pushed its branch to origin: discarded (no result recorded; the branch is deleted,
as is `bench/finance-solo`, pushed by the 09:22 run). Team leads never used either.

## Kit 3.11 (no test helper named after a test-framework method), 4 runs on v2.1

| Metric | Kit 3.11 (n=4) | Kit 3.10 (n=4) | Solo (n=4) |
|---|---|---|---|
| Hidden tests passed | 42 (41-42) | 42 (41-42) | 42 (42-42) |
| Review overall | 7 (7-7) | 6.5 (5-7) | 7 (6-7) |
| Review tests | 7 (7-8) | 5.5 (3-8) | 6.5 (6-7) |
| Runs with a shadowed `fail` | 0 of 4 | 2 of 4 | 0 of 4 |
| Cost $, cold start | 0.832 (0.654-0.866) | 0.676 (0.604-0.774) | 1.154 (1.098-1.319) |
| Teammates / lead turns | 6.5 / 17.5 | 5 / 15 | - / 15 |

- **Quality:** the bug it targets is gone (0 of 4 runs vs 2 of 4), and the review is 7 in every
  run. Against solo: ties on hidden tests and review, cheaper (-28%), all stable.
- **Cost:** 23% above 3.10, stable at 4 runs. But a lead turn costs the same in both kits
  ($0.030-0.040) and so does a teammate ($0.021-0.032): these leads chose more teammates and
  took more turns. The 3-line rule can't account for that; the lead's own team-size choice is
  the largest source of cost spread left, and n=4 doesn't separate it from the kit.
- **Adopted** (quality first): kit 3.11 is the current kit.
- `run 20261018T034038Z-team`: the reviewer put `overall` inside `scores` (7); the runner now
  accepts both places, and this run's record was corrected.

## One teammate at a time (arm team1, kit 3.11), 4 runs on v2.1

The same kit; the prompt says "Work with team on it, one teammate at a time." In every run the
lead ran its tasks in order, one teammate each (5-8 teammates, none overlapping).

| Metric | One at a time (n=4) | Parallel, kit 3.11 (n=4) | Solo (n=4) |
|---|---|---|---|
| Hidden tests passed | 41 (41-42) | 42 (41-42) | 42 (42-42) |
| Review overall | 7.5 (7-8) | 7 (7-7) | 7 (6-7) |
| Review consistency | **8** (7-8) | 6 (6-7) | 7 (7-8) |
| Review tests | 8 (8-8) | 7 (7-8) | 6.5 (6-7) |
| Cost $, cold start | 0.773 (0.722-0.921) | 0.832 (0.654-0.866) | 1.154 (1.098-1.319) |
| Wall minutes | 28 (28-29) | 14 (11-17) | 7 (7-8) |

- Against parallel (leave-one-out): consistency better (stable, above the floor), review overall
  and tests tie, cost 7% lower (stable, under a 10% minimum effect), hidden tests one lower
  (stable), wall time twice as long.
- The hidden-test miss is the same in 3 of 4 runs: `recurring add` with a start in a closed
  month is rejected, because the teammate validated the template through the shared posting
  function, which also checks closed periods (the spec checks only the posting rules when a
  schedule is added). Building on existing code made that reuse likelier (parallel: 1 of 4).
- Against solo: ties on review, consistency and structure; cheaper (-33%); one hidden test lower.
- Offered as a choice in the prompt (README); kit 3.12 documents it in the skill, with a line on
  reuse that adds checks the spec doesn't ask for. Not re-measured.

## Research-brief items, one run each (finance v2.1, base kit 3.12)

Each item from the research brief as one single-change variant (`bench/variants/`) or arm, run
once to see whether it holds before any 4-run check. Baseline: kit 3.11, 4 runs: hidden 42
(41-42), review 7 (7-7), consistency 6, $0.832 cold, 14 minutes. Solo Sonnet: 42, 7, $1.154.

| Item | Run | Hidden | Review (consistency) | Cold $ | Minutes | Teammates | Advisor calls |
|---|---|---|---|---|---|---|---|
| force-haiku | 20261018T100350Z-team | 42/42 | 7 (7) | 0.830 | 19 | 6 | 0 |
| intake-hook | 20261018T100420Z-team | 41/42 | 7 (7) | 0.645 | 11 | 5 | 0 |
| done-gate (fixed hook) | 20261018T105214Z-team | 42/42 | 7 (6) | 0.716 | 15 | 6 | 0 |
| audit | 20261018T103345Z-team | 42/42 | 7 (7) | 0.888 | 22 | 6 | 0 |
| advisor-haiku | 20261018T105244Z-team | 40/42 | 7 (6) | 0.745 | 13 | 8 | 0 |
| workflow (not available) | 20261018T110214Z-team | 42/42 | 7 (6) | 0.972 | 13 | 9 | 0 |
| solo-haiku | 20261018T100450Z-solo | 42/42 | 7 (8) | 0.312 | 36 | 0 | 0 |
| solo-haiku-advisor | 20261018T115647Z-solo | 0/42 | 3 (3) | 0.334 | 19 | 0 | 1 |
| team-haiku-lead | 20261018T115617Z-team | 42/42 | 7 (6) | 0.376 | 27 | 13 | 0 |

- **force-haiku** (item 1): holds; every teammate on Haiku, cost as 3.11. Safety only: all
  earlier runs already used Haiku.
- **intake-hook** (item 2): the hook ran on every teammate Bash call and never had to change one
  (teammates already pipe their test output). Harmless; no effect on finance.
- **done-gate** (item 3): the first run (20261018T103315Z-team) is invalid: the hook ran the
  plan's `python ...` checks where only `python3` exists and blocked every teammate twice. Fixed
  (717f071); the rerun ran each teammate's done check on idle, all passed, nothing blocked.
  Harmless; finance gives it nothing to catch. It did expose that the lead's done checks don't
  run as written on this machine.
- **audit** (item 5): the Haiku auditor found real issues for $0.02, but acting on them cost the
  lead ~$0.06 more and the review stayed 7. No gain, like the consistency pass retired in 3.10.
- **advisor-haiku** (item 6): the advisor was attached to every teammate, and Haiku never called
  it in 36 responses. Inert.
- **workflow** (item 7): not tested. Dynamic workflows aren't enabled for this account (no
  Workflow tool, no `/workflows`); the lead fell back to Agent teammates. Needs workflows turned
  on (`/config`, "Dynamic workflows").
- **solo-haiku**: one Haiku session matched solo Sonnet (42/42, review 7, consistency 8) at
  $0.312 (-73%), but took 36 minutes (Claude Code's default compaction kept it under 100K: 9
  compactions, peak 67K).
- **solo-haiku-advisor**: failed: 0/42, review 3. It built `account add` with a different
  argument shape from the spec and only checked against its own 128 tests; one interface
  mistake fails every hidden test. Its one Sonnet advisor call cost $0.179, 54% of the run.
- **team-haiku-lead**: a Haiku lead with Haiku teammates matched the Sonnet-lead team (42/42,
  review 7) at $0.376 (-55% vs kit 3.11), 27 minutes, 13 teammates, 395 own tests. It never
  called its Sonnet advisor.
- Not run: item 4 (scout: finance starts empty) and the sequential benchmark (needs a prompt).
- **Next:** 4-run checks of team-haiku-lead and solo-haiku (the second Haiku solo run's total
  failure says one good run is not enough). force-haiku can go into the kit as a safety change.
