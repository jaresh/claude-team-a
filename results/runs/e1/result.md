# Run e1 result: rules v0 (A) vs rules v1 (B)

Feature: phone camera and inventory panel (`results/runs/e1/spec.md`). Same spec, same teammate
prompts word for word, same acceptance command. Base `run/e1/base` (445f130); B adds the rules v1
commit b36fdaf (fresh lead session per run, rules L1-L4, lean `dev` teammate agent).

## Verdict

Both variants were accepted on the first check. B cost about half as much: $0.218 against $0.445
(-51%). Almost all of the saving is on the lead: $0.198 against $0.421 (-53%). B's lead started
fresh and peaked at 48K context. A's lead was a long session that peaked at 320K, with 5 messages
over 100K. Team cost fell from $0.024 to $0.021 (-13%). That is under the protocol's 20% noise
bar, so it is not a result yet.

## Numbers

| Metric | A (v0) | B (v1) | Change |
|---|---|---|---|
| Window (UTC) | 20:21:18-20:22:53 (1:35) | 20:30:15-20:32:02 (1:47) | +12 s |
| Total $ | 0.445 | 0.218 (raw report 0.395, see note 1) | -51% |
| Lead $ | 0.421 | 0.198 | -53% |
| Team $ | 0.024 | 0.021 | -13% (noise) |
| Lead msgs / tool calls | 5 / 6 | 8 / 8 | +3 / +2 |
| Lead cache read tokens | 1,585,661 | 353,184 | -78% |
| Lead peak ctx, msgs over 100K | 320K, 5 | 48K, 0 | |
| Team tool calls (view + screen) | 19 (8 + 11) | 28 (9 + 19) | +9 |
| Team peak ctx (view / screen) | 48K / 61K | 24K / 40K | -51% / -34% |
| Team output tokens | 6,936 | 14,984 | +116% |
| Handoffs, successors | 2, 0 | 2, 0 | |
| Accepted on first check | yes: 95/95, 8/8, smoke 5/5 | yes: 94/94, 8/8, smoke 5/5 | |
| Lead fixes after merge | 0 | 0 | |

Sources: `results/metrics/e1-A.json` (on `run/e1/A`), `results/metrics/e1-B.json`.

## What differed in the code

- `input.js`: A added a guard in `buttonToAction` for a bad `data-index`. B left the file alone:
  the click handler already delegates any `[data-action]` click, so the new inventory buttons
  work unchanged (smoke `inputWorks` passes). The contract only requires taps to work.
- Test count: 95 for A, 94 for B. The teammates wrote different unit tests: B's view has 6 tests
  and screen has 7.
- Neither variant wrote a `results/changes.md` row. `game.js` is a module owned by the task, not
  a shared generator, so none was needed.

## Measurement notes

1. **Another session in B's window.** Session `55f7d26e` (A's lead) made 2 calls during B's
   window, at 20:31:36-20:31:52, costing $0.176 at a 342K peak. That work is not part of B, so it
   is subtracted above. `e1-B.json` is the raw report and still includes it. For later runs:
   keep other sessions idle during a window, or give `teamcost.py` a session filter.
2. **Effort column blank for `dev`.** `teamcost.py` reads effort from the subagent
   `.meta.json`. For a custom agent type, that file has no `effort` key. The transcripts show
   `"effort":"medium"` on every request from both teammates (45 for screen, 28 for view), so the
   rule was followed and only the report is missing it. Fix: fall back to the transcript.
3. **Not counted, in either variant:** lead work after the window ends (comparison, write-up,
   commit, push).
4. **B teammates did more work for less money.** They made more tool calls and wrote twice the
   output, but each call re-read a smaller prompt, because the `dev` agent has 6 tools and a short
   system prompt. Whether this nets out lower is within noise for one run.

## Open

- Repeat both variants to confirm the team-side difference, which is under 20%. The lead-side
  difference (-53%) is large enough to keep rules v1's L1 (fresh lead session per run).
- Fix the `teamcost.py` effort fallback, and add a session include/exclude option.
- B's lead floor is about 40K context (system prompt, CLAUDE.md and the spec) times 8 turns. The
  next saving is fewer lead turns per wave.
