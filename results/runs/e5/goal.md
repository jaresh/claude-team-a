# Run e5: score, stats and high scores (goal only)

Run e5 (design: `results/runs/e5/spec.md`). Plan and run the team with the `/team` skill's own
steps; there are no prepared teammate prompts.

## Goal

Add two features to the game, per their contract sections in `game/ARCHITECTURE.md`:

1. **Score and stats**: "e5: score and stats".
2. **Run summary and high scores**: "e5: run summary and high scores".

`game/accept/` and `game/sim/` are yours (the lead's): teammates don't edit them. The browser
check in the command below is yours too.

## Check (run it once after the merge; one fix round at most)

```
npm test && node --test "game/accept/*.test.js" && node game/tools/smoke.mjs out/e5/<variant>.png --ids inventory,hpbar,end,legend,help,scores
```

## When the check passes

1. Copy the team's files: `cp -r .claude/team results/runs/e5/<variant>-team`.
2. Write `results/runs/e5/<variant>.md`: at most 5 lines (check result, fix rounds, successors,
   anything odd).
3. Write `date -u +%FT%TZ` to your end-time file (named in your first message), commit
   everything on the branch and push.
4. Tell the user: "Run done. Type /exit; lab/run.sh will measure it."
