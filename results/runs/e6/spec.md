# Run e6: pilot of the plain-prompt flow (shop)

Not an A/B run: one session started the way the user works. A new session in the repo, a
plain request ("work with team on it, write tests and deploy on staging"), no contract and no
acceptance tests written in advance. Kit 3.6, lean lead (`team_kit.py lead` flags), Sonnet 5.5
at effort medium, 1-hour cache.

    LEAD_ARGS="$(python3 team_kit.py lead --print-args)" lab/run.sh --bg results/runs/e6/prompt.md A

The prompt is `results/runs/e6/prompt.md`, word for word; its last paragraph is testbed
bookkeeping (no one answers questions in an unattended run, and the run is committed).

Quality is judged afterwards, without a fixed acceptance file:

- No regression: `npm test` and `node --test "game/accept/*.test.js"` (the e1-e5 acceptance
  suites and the e2 balance targets) pass.
- The lead's own tests: written before the team started, failing on the base, and specific
  enough to catch a broken shop (reviewed by the planning session).
- Staging: the deployed copy works (`npm run stage` smoke test, then the URL is checked).
- No change outside the plan; the report lets the user assess the work.
