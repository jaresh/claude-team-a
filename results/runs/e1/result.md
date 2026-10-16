# Run e1 result: rules v0 (A) vs rules v1 (B)

## Correction (lead of the planning session, after the run)

Remeasured with `teamcost.py --session 336f559a --until 2026-10-16T20:40:56Z`: B cost **$0.360**,
**19% less** than A, not $0.319 / 28%. B's lead measured itself while its last message was
still being written, so that message was missed. Table from `teamcost.py --compare`:

| Metric | A | B | B vs A |
|---|---|---|---|
| Total $ | 0.445 | 0.360 | -19% |
| Lead $ | 0.421 | 0.341 | -19% |
| Team $ | 0.024 | 0.020 | -18% |
| Lead model | opus-5-5 | opus-5-5 |  |
| Lead cache read $ | 0.317 | 0.066 | -79% |
| Lead cache write $ | 0.053 | 0.175 | +228% |
| Lead output $ | 0.051 | 0.099 | +96% |
| Lead messages | 5 | 8 | +60% |
| Lead tool calls | 6 | 9 | +50% |
| Lead output tokens | 2527 | 4952 | +96% |
| Lead peak context | 320K | 49K | -85% |
| Teammates | 2 | 2 | +0% |
| Team tool calls | 19 | 23 | +21% |
| Team peak context | 61K | 39K | -35% |
| Team messages over 100K | 0 | 0 |  |


The original write-up follows; its dollar figures for B are the uncorrected ones.


Same spec, same base (`run/e1/base`, 445f130), same teammate prompts and acceptance command.
Reports: `results/metrics/e1-A.json` (branch `run/e1/A`), `results/metrics/e1-B.json`.

**Verdict.** B built the same feature and passed acceptance on the first check, for 28% less
($0.319 vs $0.445). Nearly all of the saving is in the lead's context: the v1 lead peaked at 47.5K
tokens, against 320K for the long v0 session. The gap is above the protocol's ~20% noise
threshold, but it comes from one run per variant.

## Numbers

| Metric | A (v0) | B (v1) | B vs A |
|---|---|---|---|
| Total $ | 0.445 | 0.319 | -28% |
| Lead $ | 0.421 | 0.299 | -29% |
| Team $ | 0.0240 | 0.0196 | -18% |
| Lead msgs / tool calls | 5 / 6 | 7 / 7 | +2 / +1 |
| Lead peak context | 320K | 47.5K | -85% |
| Lead msgs over 100K context | 5 | 0 | |
| Lead cache read / write | 1,586K / 6.7K | 285K / 20.7K | |
| Team tool calls | 19 (screen 11, view 8) | 23 (screen 17, view 6) | +4 |
| Team peak context | screen 61K, view 48K | screen 39K, view 22K | -36% / -55% |
| Team cache write | 109K | 61K | -44% |
| Team output tokens | 6.9K | 13.0K | +87% |
| Wall time (start to end) | 95 s | 114 s | +19 s |
| Accepted on first check | yes | yes | |
| Tests (npm test) | 95/95 (+14 new) | 91/91 (+10 new) | |
| Acceptance / smoke | 8/8, 5/5 | 8/8, 5/5 | |
| Lead fixes after merge | none (one run commit) | none | |

## Where the lead's money went (teamcost prices)

| Component | A | B |
|---|---|---|
| Cache read ($0.20/M) | $0.317 (75%) | $0.057 (19%) |
| Cache write, 1h ($8/M) | $0.053 (13%) | $0.166 (55%) |
| Output ($20/M) | $0.051 (12%) | $0.076 (25%) |

- In v0 every lead turn re-read a 320K context. In v1 the lead starts fresh, so it pays once to
  write its starting context to the cache, and each turn then reads a small context.
- In B the lead's largest cost is that one cache write. Most of it is the system prompt and the
  tools, which the rules can't change, so lead turns and output are the next things to cut.

## Team

- The lean `dev` agent roughly halved teammate context: peaks of 39K and 22K, against 61K and 48K.
  Team cost fell 18%.
- B's `screen` made 6 more tool calls and wrote twice as much output, partly because it added a
  stub-DOM render check in its scratch folder. Team cost is about 6% of the total in both
  variants, so the lead still dominates.

## Caveats

- n = 1 per variant.
- The two variants were counted differently, as the protocol says. A counted a time window inside
  a long session (`--since/--until`): turns before the window are not counted, but their tokens
  are re-read in every turn inside it. B counted the whole fresh session (`--latest-session`),
  which includes reading the spec.
- Neither total includes the lead's work after the end time (the comparison, this file, the
  commit).
- In B, teamcost leaves the effort column empty for `dev` teammates. `dev.md` sets
  `effort: medium` and the lead passed `effort: "medium"`, but the report can't confirm it from the
  transcript, so this is a gap in the tool.
- Quality is close, not identical. B added fewer unit tests (10 vs 14). In `out/e1/B.png` the
  "Inventory empty" label wraps onto two lines inside the panel's 2-column grid; this is cosmetic.
  A's screenshot was not compared.
- On branch A, the e1-A row in `results/experiments.md` follows a blank line, so it renders
  outside the table. Fix this when the branches are merged.
