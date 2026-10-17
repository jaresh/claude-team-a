# e6 review (planning session)

Pilot of the user's flow: a new session, a plain request ("work with team on it, write tests
and deploy on staging for me to assess"), kit 3.6, lean lead (Sonnet 5.5, medium).

**Cost.** $0.436 ($0.478 at a cold start): lead $0.398 (17 messages; cache read $0.149, cache
write $0.172, output $0.077 for 7.7K tokens: the plan, a 120-line acceptance test, two
teammate prompts, the report), team $0.038. About 4 lead turns went to a staging problem
(below), so a clean run would be near $0.40.

**Flow.** Loaded the team skill first; read the contracts with `head` and line ranges (3
turns); in one turn wrote the plan (assumptions listed, precise contract), wrote
`game/accept/e6-shop.test.js` and ran it to see it fail; started `core` and `ui` in parallel;
merged; one check passed (167 tests, 52 acceptance tests, e2 balance). No fix round, no change
outside the plan.

**Tests.** Real: starting gold, gold per kill, the shop open only on its tile, buying needs
gold and the shop tile, costs gold, takes no turn, gold kept across levels, stock by depth. A
broken shop fails them. The UI panel is covered by unit tests and the smoke test, not by play.

**Staging.** A testbed bug, not the kit's: `npm run stage` derived the staging folder from the
checkout path, so in the run's worktree it pointed at a folder the server on port 8100 (started
from the main checkout) didn't serve. The lead's first two workarounds were refused by the auto
mode classifier (an `rm -rf` outside its worktree; deploying into another checkout's served
folder), which was right. It then deployed on port 8101, which works. Fixed: every worktree now
shares the main checkout's staging folder, and a server that serves another folder is refused
before anything is copied.

**Verdict.** The plain-prompt flow works at the same quality as a prepared spec, for about 1.5x
the cost of e5 (a bigger feature, plus the lead writing the contract and tests). Main has not
merged the shop; it is on `run/e6/A`, staged at http://127.0.0.1:8101/shop-A/game/ for the user.
