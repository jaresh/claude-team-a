# Archive

Features of the kit and the testbed that were tried and retired: what each did, why it went, and
how to bring it back. Results are in `bench/finance/results/REFERENCE.md`.

| Retired | What it was | Why | Bring it back |
|---|---|---|---|
| Kit 3.10 (2026-10-17) | **Consistency pass**: after the last wave, one more Haiku teammate, `consistency`, replaced duplicated helpers and re-implemented rules with the shared ones (kit 3.7 a paragraph, 3.8 and 3.9 its own required step 4) | Cost about $0.07 a run (one teammate plus about three lead turns) and didn't raise the review's consistency score: median 6.5 over 4 runs with it, 6, 7 and 6 without. Running one teammate at a time did more (consistency 8) | `git show 75df800:team_kit.py`, section "## 4. Consistency pass", and the `consistency` rows in steps 1 and 2 |
| 2026-10-18 | **`audit` variant**: after the last wave, a fresh-context Haiku teammate lists findings (requirement not met or untested, a rule implemented twice, a convention broken) without changing files; the lead fixes them or starts `audit-fix` | One run (20261018T103345Z-team): the auditor found real issues for $0.02, but acting on them cost the lead about $0.06 more turns and the review stayed 7 (42/42, $0.888 vs kit 3.11's $0.832) | `git show 629f198:bench/variants/audit.py > bench/variants/audit.py` |
| 2026-10-18 | **`advisor-haiku` variant**: `advisorModel: claude-haiku-5-5` in the kit's settings, so Haiku teammates can consult a Haiku advisor (the Sonnet lead accepts none below Sonnet 5.5) | One run (20261018T105244Z-team): the advisor was attached to every teammate and Haiku never called it in 36 responses; no effect | `git show 629f198:bench/variants/advisor-haiku.py > bench/variants/advisor-haiku.py` |
