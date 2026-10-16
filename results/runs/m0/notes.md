# Run m0 notes (rules v0)

## Outcome

- 5 teammates in 3 waves (world, rules, ui | game | sim), 9 minutes wall time.
- Merge checks: 62/62 after wave 1, 78/78 after wave 2, 81/81 after wave 3. No teammate touched
  a file it didn't own. All 5 handoffs written. No change-log rows (no shared file edited).
- Browser smoke test (headless Chromium, 360 px): no errors, no horizontal scroll, keys and
  buttons work. The 60x30 map renders at ~5 px per tile: hard to play on a phone.
- Bot, 200 seeds: 0 wins, mean depth 2.3, mean 166 turns; goblins cause 60% of deaths.

## Cost

| Who | Messages | Tool calls | Peak context | Cost |
|---|---|---|---|---|
| Lead (Opus 5.5, xhigh) | 25 | 34 | 282K | $2.24 (97%) |
| 5 teammates (Haiku 5.5, medium) | 39 | 52 | 36-73K | $0.069 (3%) |

Lead cost split: cache reads $1.30 (6.5M tokens), output $0.58, cache writes $0.36.

## Findings (candidates for rules v1)

1. **The lead is the cost.** Every lead turn re-reads the whole lead context (~260K tokens here,
   ~$0.05 per turn in cache reads alone). Cache reads cost the same on Sonnet 5.5 as on Opus 5.5,
   so the lever is the lead's context size and turn count, not the lead's model.
   Candidate: start each run in a fresh lead session that reads only CLAUDE.md, the spec and the
   handoffs. This is what the handoff files make possible.
2. **Lead bookkeeping costs more than teammates.** 10 lead edits to `team-status.md` and the prompt
   log; each lead turn costs about as much as a whole teammate. Candidate: update the status file
   once per wave, and only rows the team config lacks (task, state, handoff, jobs).
3. **Teammate base context is ~33K tokens** (system prompt, tool definitions, CLAUDE.md) before
   any work: a third of the 100K budget. Candidate: a custom agent type with fewer tools.
4. **Rule 20 (TaskStop) is a no-op.** A teammate that hands back is already stopped; TaskStop
   errors with "not running".
5. **"Teammates don't run the full suite" is too broad.** `game` ran `npm test` (0.14 s).
   Candidate: define heavy jobs by run time (over ~1 minute), not by name.
6. **Handoffs were used.** `game` read three wave-1 handoffs for the details it needed
   (0-based `use` index, entity ids, the import line to change).
7. **Budget rule never triggered.** Max 16 tool calls, max 73K context; tasks were sized well
   below the 40-call / 100K limit.

## Measurement caveat

Teammate transcripts store the usage from the start of each response, so their output tokens are
estimated from visible content (`out_est` column, 3.5 chars/token). Hidden thinking is not
counted, so team cost is a lower bound. The lead's numbers are exact.
