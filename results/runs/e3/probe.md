# Probe: does a 100K auto-compact window reach Haiku teammates?

Background session (Haiku lead, low effort) started with
`--settings '{"modelSettings":{"claude-haiku-5-5":{"autoCompactWindow":100000}}}'`, one `dev`
teammate told to read a 488 KB file in ten 500-line Read calls. Measured with teamcost.py.

| Agent | Messages | Peak context | Messages over 100K | Compactions | Cost |
|---|---|---|---|---|---|
| lead | 4 | 45K | 0 | 0 | $0.006 |
| reader2 | 3 | 242K | 1 | 1 | $0.144 |

- The teammate issued all ten reads in parallel; its prompt went from 18K to 242K in one step.
- Auto-compaction then ran (one compact boundary) and brought the context back to 21K.
- So the setting reaches teammates, but compaction can't prevent the one oversized turn, which
  is billed at Haiku's 5x rate above 100K.
- A first attempt with 1000-line reads failed: those reads were too large for the Read tool, so the
  context never grew (prompts stayed near 20K).
