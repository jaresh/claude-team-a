# Change log

One line per edit to a shared generator, config or table (rule 13). Append at the end.

| Date | Teammate | File | Function or row | What changed |
|---|---|---|---|---|
| 2026-10-16 | view | game/src/core/game.js | getView | added `player` {x,y} and `inventory` entries (e1 View additions) |
| 2026-10-16 | tuner | game/src/core/game.js | PLAYER_START | hp 20 -> 30 |
| 2026-10-16 | tuner | game/src/core/rules.js | spawnMonsters | count 3 + 2*depth -> 2 + depth |
| 2026-10-16 | tuner | game/src/core/rules.js | spawnItems | count 2 + floor(depth/2) -> 4 + floor(depth/2) |
| 2026-10-16 | tuner | game/src/data/monsters.js | goblin | atk 3 -> 1 |
| 2026-10-16 | tuner | game/src/data/monsters.js | kobold | atk 2 -> 1 |
| 2026-10-16 | tuner | game/src/data/monsters.js | orc | atk 4 -> 2, hp 14 -> 8 |
| 2026-10-16 | tuner | game/src/data/items.js | potion | heal amount 8 -> 12 |
| 2026-10-16 | tuner | game/test/rules.test.js | spawn count tests | assertions updated to the new spawn counts (2 + depth, 4 + floor(depth/2)) |
| 2026-10-16 | abilities | game/src/data/monsters.js | every row | added `ability` field: bat poison, orc ranged, troll regen, others null |
| 2026-10-16 | abilities | game/src/data/monsters.js | spider (new, appended) | glyph s, hp 4, atk 2, def 0, xp 4, minDepth 3, ability poison |
| 2026-10-16 | abilities | game/src/data/monsters.js | goblin | ability null (regen tried first; win rate fell to 9%, goblins were 40% of deaths) |
| 2026-10-16 | abilities | game/src/core/rules.js | spawnMonsters | copies `ability` onto each monster |
| 2026-10-16 | abilities | game/src/core/rules.js | monsterStep | returns `shoot` for ranged monsters at Chebyshev 2 to 4 on visible tiles |
| 2026-10-16 | abilities | game/src/core/game.js | monsterPhase, endTurn, getView, newGame | shoot, regen, poison (3 turns), hud.poison, visibleMonsters, player.poison |
