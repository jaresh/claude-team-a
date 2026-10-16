# Project working rules (team setup and token budget)

Paths are relative to the repo root (the work dir is the repo). It applies to the lead (the main
agent) and to every teammate (subagent) it starts.

## Roles

- **Lead.** Owns the plan, the shared state, every heavy job (rule 8), merges teammates' changes,
  commits, and decides anything that changes the design. Keeps `results/team-status.md` up to
  date.
- **Teammate.** Does one bounded task, writes its results to files, and stops. It never starts a
  new task on its own.

## Lead sessions

The lead re-reads its whole context on every turn, so the lead's context size, not the
teammates, is most of the cost.

- L1. Plan in one session, run in another. The planning session writes the run's spec,
  `results/runs/<run>/spec.md`: goal, contract sections, teammate prompts, acceptance command,
  lead steps. Each run then starts in a fresh lead session, `kit/run.sh <spec> [variant]`, that
  reads CLAUDE.md, the spec and the files the spec names. It does not rely on earlier
  conversations.
- L2. One lead turn per wave for bookkeeping: update the status file in the same turn as the
  spawns, and again in the same turn as the merge check. Do not re-read a file you just wrote.
- L3. After spawning, end the turn. Completion notices wake the lead; do not poll.
- L4. From a handoff, read Done and Next step; read the rest only when a decision needs it.
- L5. A run lead follows a written spec, so it runs on Sonnet 5.5 at effort `medium` with a
  5-minute prompt cache (the `kit/run.sh` defaults). The cache expires after 5 idle minutes: for
  waves that take longer, start the run with `CACHE_TTL=1h`.
- L6. The run lead does not measure its own session or write cost tables. When the run is done
  and accepted, it writes the end time (`date -u +%FT%TZ`) to the end-time file `kit/run.sh`
  named, commits and pushes, and asks the user to type `/exit`. `kit/run.sh` then measures the
  finished session and compares variants with `kit/tools/teamcost.py`.

## Budget

1. A teammate works to about 100K tokens, roughly 40 tool calls. At the next safe point past
   that, it stops and writes a handoff. It does not start a new step. Above 100K tokens of
   prompt, Haiku 5.5 costs 5x.
2. Every teammate runs on Haiku 5.5 at reasoning effort `medium`, as agent type `dev`
   (`.claude/agents/dev.md`, installed from `kit/agents/`). The lead always passes
   `model: "haiku"` and `effort: "medium"` to the Agent tool, and never starts a teammate on
   another model. If `dev` is not installed, use `general-purpose`. Raise the effort only when the
   user asks for a specific task at a higher level.
3. The lead counts the budget from tool calls and from the token counts in completion notices.
   A teammate's own estimate is the best measure available.

## Handoff

4. Before the final message, a teammate writes `results/handoff/<name>.md` with four
   sections: **Done** (files and rows changed, counts, test results), **In progress** (where it
   stops), **Next step** (the exact next action and command, runnable without the history),
   **Do not redo** (what was checked and ruled out, with evidence). The handoff must exist before
   the final message. The final message is one status line plus the handoff path.
5. The lead checks that the handoff exists before it starts a successor. If it is missing, the
   lead writes it from the report.
6. A successor reads the handoff and the files it names, not the old transcript. Its name is the
   same base name with a number suffix (`<task>-2`, `<task>-3`), so the chain is visible.

## Jobs and parallel work

7. A teammate never hands back while a job it started is still running. If the job must keep
   running, the handoff names its output file, the exact done check, and the command that reads
   the result. A teammate never reports a partial count as final.
8. A heavy job runs longer than about a minute or holds a shared resource (CPU, disk, a game
   process). The lead starts one heavy job at a time per resource and records it in the status
   file. Teammates read heavy-job output files; they do not start heavy jobs. Quick checks (a test
   suite or syntax check that finishes in under a minute) are not heavy: anyone may run them.
9. Before and after numbers use the same file list. The list is written once, to a file, and
   both runs read it. A count is not repeated when it is already in a handoff.
10. Test on a small sample before a full run. The full run happens once the sample is right.

## Files and scratch

11. Each teammate writes its own scratch files only in `scratch/<name>/`. Never the
    shared scratchpad, never another teammate's folder, never the repo unless its task says so.
12. Generated output goes to a new empty folder each time. Never overwrite a baseline that another
    teammate is measuring against.
13. Each edit to a shared generator or config is logged with one line in
    `results/changes.md`: date, teammate, file, function or row, what changed. Merging
    reads the log, not the diff.
14. Shared tables are changed by appending rows at the end, with the Edit tool, unless the task
    says to change values in existing rows (log each change, rule 13). Never rewrite the whole
    file. Never edit a file while another teammate is editing it.

## Reports and token use

15. A final report is short: what changed (paths, names), counts, what is still open, the handoff
    path. Target under 150 words. Put detail in files, and point to them.
16. Ask a teammate for counts and paths, not logs. Logs stay in files and are read with grep or
    `tail -n`, never in full.
17. The lead does not read a teammate's transcript output file. It reads the handoff and the
    result files the teammate names.
18. Do not repeat a check whose result is already in a handoff's Done or Do-not-redo section.

## Lead housekeeping

19. `results/team-status.md` has one row per teammate (name, task, model, effort,
    state, handoff path) and one row per heavy job (what, output file, done check). Update it
    once per wave (L2): when the wave starts and at its merge check, and when a job starts or
    finishes.
20. A teammate that has handed back is already stopped; do not call TaskStop on it. Use TaskStop
    only for a teammate that is still running and must not continue. Check the status file first,
    so a running job is not cut off.
21. Before merging, the lead reads the change log and the handoffs (L4), and runs one check on the
    merged result. Reports from several teammates are not trusted until that check passes.

## Repo rules

- The lead commits and pushes once at the end of each run, on the run's branch (the user allowed
  this). Teammates never commit.
- Generated sources, object files and large working data live in `out/` or `scratch/` (gitignored),
  never in tracked files.
- Teammates do not run heavy jobs (rule 8) or launch the target program. The lead owns those.
- Edits to shared generators or configs are small, with the Edit tool. Never rewrite a shared
  file as a whole.
