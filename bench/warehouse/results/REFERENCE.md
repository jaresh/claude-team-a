# Warehouse benchmark: reference results (version 219b3f7797b5)

## Pilot, 2026-10-19: one run per arm

`bench/warehouse/prompt.md` (fourteen sections) built by Sonnet 5.5 alone (no subagents) and by a
Sonnet 5.5 lead with Haiku 5.5 teammates (kit 3.13), both at effort medium with the 1-hour cache.
Scored with the 62 hidden tests in three tiers, `bench/quality.py`, a blind Opus review and a blind
Sonnet review (`REVIEW2_MODEL=sonnet`). One run each, so these are not yet medians: the question
was whether the benchmark spreads scores where finance sat near its ceiling.

| Metric | solo | team, kit 3.13 |
|---|---|---|
| Run | 20261019T032702Z-solo | 20261019T032632Z-team |
| Hidden tests passed | 59/62 | 61/62 |
| T1 one feature | 30/31 | 30/31 |
| T2 features combined | 21/21 | 21/21 |
| T3 robustness | 8/10 | 10/10 |
| Own tests passed | 14/14 | 108/108 |
| Own tests' line coverage | 0.817 | 0.930 |
| App lines / test lines | 1685 / 282 | 2068 / 1206 |
| Max complexity / functions over 10 | 46 / 14 | 19 / 8 |
| **Review overall, Opus** (1-10) | 7 | 7 |
| Opus: structure, readability | 6, 5 | 7, 7 |
| Opus: correctness, errors, data | 7, 6, 8 | 7, 7, 9 |
| Opus: tests, consistency | 6, 7 | 6, 7 |
| **Review overall, Sonnet** (1-10) | 6 | 7 |
| Sonnet: structure, readability | 6, 5 | 7, 7 |
| Sonnet: correctness, errors, data | 6, 8, 8 | 6, 8, 8 |
| Sonnet: tests, consistency | 5, 7 | 6, 7 |
| Total $, cold start | 1.513 | 1.582 |
| Lead / solo $ | 1.513 | 1.326 |
| Team $ | 0 | 0.257 (8 teammates) |
| Lead / solo messages | 13 | 28 |
| Lead / solo peak context | 118K | 95K |
| Wall minutes | 9.8 | 30.1 |

Hidden test failures:

- solo, three tests with one cause: a `viewer` can write (`receive` and `move` on the CLI,
  `POST /receipts` over HTTP), where section 1 allows viewers only commands that read
  (`T1Users.test_roles_and_last_admin`, `T3Permissions.test_viewer_and_clerk`,
  `T3Http.test_products_paging_and_auth`).
- team, one test: a receipt's `serials` keep the order given (`P2,P1`) instead of ascending, which
  the general rule asks for ("where nothing is stated, by id or code, ascending";
  `T1Receive.test_receive_rules`).

Reading:

- The benchmark spreads scores. Reviews land at 6-7 with sub-scores from 5 to 9, against 7-9 on
  finance. The hidden tests catch a real spec miss in each arm, and T3 tells the arms apart.
- On quality the team is level or ahead on one run: +2 hidden tests (both T3), Sonnet review +1,
  readability +2 in both reviews, a quarter of solo's peak complexity, four times the test lines.
- On cost the finance saving is gone: the team costs 5% more, with three times the wall time.
  Solo built the whole app in 13 messages. The lead's 28 messages cost about as much as all of
  solo, so the teammates' $0.26 is added on top.
- Next, on request: four runs per arm and the `bench/spread.py` stability check before any
  conclusion.

## Second run per arm, 2026-10-19

| Metric | solo 2 | team 2, kit 3.13 |
|---|---|---|
| Run | 20261019T051705Z-solo | 20261019T051635Z-team |
| Hidden tests passed (T1 / T2 / T3) | 62/62 (31 / 21 / 10) | 61/62 (30 / 21 / 10) |
| Own tests passed, coverage | 11/11, 0.851 | 129/129, 0.918 |
| App lines / test lines | 1822 / 275 | 2277 / 1338 |
| Max complexity / functions over 10 | 27 / 12 | 28 / 6 |
| Review overall, Opus / Sonnet | 6 / 6 | 7 / 7 |
| Opus: structure, readability, correctness | 6, 6, 6 | 7, 8, 7 |
| Opus: errors, data, tests, consistency | 6, 8, 6, 6 | 7, 8, 7, 7 |
| Sonnet: structure, readability, correctness | 6, 6, 5 | 7, 7, 6 |
| Sonnet: errors, data, tests, consistency | 7, 7, 4, 6 | 7, 8, 6, 7 |
| Total $, cold start | 1.679 | 1.002 |
| Lead / solo $; team $ | 1.679; 0 | 0.725; 0.277 (6 teammates) |
| Lead / solo messages, peak context | 18, 124K | 19, 68K |
| Wall minutes | 10.2 | 49.7 |

- **solo 2** passed every hidden test, but both reviewers scored it 6.
  - Opus: voiding a scrap, or returning a serial that is back in stock, raises
    `sqlite3.IntegrityError` as a traceback. Unknown SKUs over HTTP give 400 instead of 404.
  - Sonnet: tests are a few broad flows; short names and star imports; the HTTP layer reuses
    the CLI's.
- **team 2** failed the same test as team 1: receipt serials kept in the order given.
  - Solo sorted them in both runs.
  - The rule is in the spec's general conventions, so this is a spec-wide rule that doesn't
    reach the teammate who writes `receive`.
  - Review issues: idempotency keys stored outside the command's transaction, domain helpers
    inside command modules, and only `UserError` caught (sqlite errors end in a traceback).

Two runs per arm (`bench/spread.py bench/warehouse/results`):

| Metric | team, kit 3.13 (n=2) | solo (n=2) | Leave-one-out |
|---|---|---|---|
| Hidden tests passed | 61 (61-61) | 60.5 (59-62) | flips |
| Hidden T3 (robustness) | 10 (10-10) | 9 (8-10) | flips |
| Review overall (Opus) | 7 (7-7) | 6.5 (6-7) | flips |
| Review structure (Opus) | 7 (7-7) | 6 (6-6) | team, stable |
| Own tests' coverage | 0.924 (0.918-0.930) | 0.834 (0.817-0.851) | team, stable |
| Cost $, cold start | 1.292 (1.002-1.582) | 1.596 (1.513-1.679) | team, stable |
| Wall minutes | 39.9 (30.1-49.7) | 10 (9.8-10.2) | solo, stable |

- The Sonnet reviewer agrees on direction: team 7 and 7, solo 6 and 6.
- Team cost follows the lead's turns: 28 turns gave $1.58, and 19 gave $1.00. The teammates
  cost $0.26-0.28 in both runs.
- Below the method's minimum of 3-4 runs per arm, so nothing is settled yet.
