// High scores and the run summary. Pure helpers: storage is passed in, so node tests can fake it.
// render.js shows the rows; main.js adds each finished game and saves the list.

export const MAX_SCORES = 5, SCORES_KEY = 'roguelike-scores';

// Returns a new list, best first: higher score first, equal scores with fewer turns first.
// At most MAX_SCORES entries. The list passed in is not changed.
export function addScore(list, entry) {
  return [...list, entry]
    .sort((a, b) => b.score - a.score || a.turns - b.turns)
    .slice(0, MAX_SCORES);
}

// [] when the key is missing or its value isn't a JSON array.
export function loadScores(storage) {
  try {
    const list = JSON.parse(storage.getItem(SCORES_KEY));
    return Array.isArray(list) ? list : [];
  } catch {
    return [];
  }
}

export function saveScores(storage, list) {
  storage.setItem(SCORES_KEY, JSON.stringify(list));
}

// view: a View from getView(). Rows in the order the end panel shows them.
export function summaryRows(view) {
  const kills = Object.values(view.stats.kills).reduce((sum, n) => sum + n, 0);
  return [
    { label: 'Score', value: view.score },
    { label: 'Depth reached', value: view.stats.deepest },
    { label: 'Turns', value: view.hud.turn },
    { label: 'Kills', value: kills },
    { label: 'Items used', value: view.stats.itemsUsed },
    { label: 'Traps triggered', value: view.stats.trapsTriggered },
    { label: 'Damage taken', value: view.stats.damageTaken },
  ];
}
