# Change log

One line per edit to a shared file: date, teammate, file, function or row, what changed.

2026-10-17 summary mock-game.js newGame/attackMonster/endTurn/act/getView: stats tracking, view.stats and view.score (imports core/score.js)
2026-10-17 summary index.html: #end gets #summary, high-score heading and #scores list; CSS for them
2026-10-17 summary render.js: render(..., scores) param; renderEnd fills #summary and #scores via fillList
2026-10-17 summary main.js: loads scores, addScore once per finished game (recorded flag, reset on new), saves with try/catch
