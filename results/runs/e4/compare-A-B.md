| Metric | A | B | B vs A |
|---|---|---|---|
| Total $ | 0.191 | 0.267 | +40% |
| Total $, cold start | 0.289 | 0.365 | +26% |
| Lead $ | 0.156 | 0.234 | +50% |
| Team $ | 0.035 | 0.033 | -4% |
| Lead model | sonnet-5-5 | sonnet-5-5 |  |
| Lead cache read $ | 0.049 | 0.099 | +101% |
| Lead cache write $ | 0.088 | 0.105 | +20% |
| Lead output $ | 0.019 | 0.030 | +56% |
| Lead messages | 6 | 11 | +83% |
| Lead tool calls | 5 | 11 | +120% |
| Lead output tokens | 1894 | 2964 | +56% |
| Lead start-up prompt | 40K | 40K | -0% |
| Lead peak context | 48K | 52K | +9% |
| Teammates | 2 | 2 | +0% |
| Team tool calls | 41 | 53 | +29% |
| Team peak context | 62K | 61K | -3% |
| Team messages over 100K | 0 | 0 |  |
| Team compactions | 0 | 0 |  |

A: results/metrics/e4-A.json lead=sonnet effort=medium cache=1h
B: results/metrics/e4-B.json lead=sonnet effort=medium cache=1h

## Verdict

Both accepted. A (full spec) passed the first check. B (goal only: the `/team` skill planned)
passed after one lead fix, and cost 26% more at a cold start (+$0.076), all of it in the lead:
11 turns against 6. Team cost was equal (-4%).

- Planning: 3 turns (find and read the two contract sections, write a 1.3 KB `plan.md`).
- Merge: 5 turns against 2. B's plan told `traps` to keep the e2 balance test passing but not
  what it could tune for it (the "e2: balance" section allows `PLAYER_START` and more). The
  teammate tried only trap amounts, then stopped and asked (its handoff lists the options). The
  lead raised player hp 30 -> 34 itself, then logged it and updated status in separate turns.
- Both leads started from a 40K-token prompt. Written cold, that is about $0.16, over half a
  cold run; it is the cost of any new session, whatever the kit does.

Kit 3.1 from this: a plan's task names what it may change to pass its checks, and its done check
includes every check it must keep passing; the lead puts independent steps in one turn.
