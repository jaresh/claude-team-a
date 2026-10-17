# Change log

One line per edit to a shared file: date, teammate, file, function or row, what changed.

- 2026-10-17, summary, game/src/ui/scores.js: new file; addScore, loadScores, saveScores, summaryRows, MAX_SCORES, SCORES_KEY.
- 2026-10-17, summary, game/src/ui/render.js: render() takes scores (5th arg); renderEnd fills #summary and #scores.
- 2026-10-17, summary, game/src/ui/mock-game.js: newGame stats; kill/use/descend/hit counters; getView stats copy and score.
- 2026-10-17, summary, game/src/main.js: startGame, recordIfEnded, readScores/writeScores (try/catch), seed kept.
- 2026-10-17, summary, game/index.html: #summary, h2 and #scores inside #end; CSS for them.
- 2026-10-17, summary, game/test/scores.test.js: new file, 5 unit tests.
