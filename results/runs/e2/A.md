# Run e2 variant A (Opus 5.5 xhigh lead, 1h cache)
- Acceptance: pass after one lead fix (npm test 97/97, e2 accept 7/7, smoke ok with inventory,hpbar,end).
- Fix rounds: 1, by the lead, no successor. First smoke failed with noErrors=false: smoke taps the first 4 `<button>`s, and hud put the hidden `#end` New game button first in the DOM. Lead moved `#end` after `.controls` and made it a fixed overlay (logged in results/changes.md).
- Balance (tuner): 16.0% wins on the 200 seeds, only 1 point above the 15% floor. HP 20->40, monster count 3+depth, goblin/orc weaker, potion 12.
- Odd: the contract doesn't fix where `#end` goes in the DOM, and smoke.mjs relies on button order. Worth one line in the e3 contract.
