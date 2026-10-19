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
