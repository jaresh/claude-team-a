// High scores and the run summary. Pure helpers, no DOM, so node tests load them directly.
// main.js stores the list; render.js shows it and the summary rows.

export const MAX_SCORES = 5, SCORES_KEY = 'roguelike-scores';

// entry: { score, depth, turns, seed, won }. Returns a new list, best first; equal scores put
// the run with fewer turns first. The list keeps at most MAX_SCORES entries.
export function addScore(list, entry) {
  return [...list, entry]
    .sort((a, b) => b.score - a.score || a.turns - b.turns)
    .slice(0, MAX_SCORES);
}

// storage: { getItem, setItem } (localStorage). Returns [] when the key is missing or its value
// is not a JSON array.
export function loadScores(storage) {
  const raw = storage.getItem(SCORES_KEY);
  if (raw === null) return [];
  try {
    const list = JSON.parse(raw);
    return Array.isArray(list) ? list : [];
  } catch {
    return [];
  }
}

export function saveScores(storage, list) {
  storage.setItem(SCORES_KEY, JSON.stringify(list));
}

// view: a View from getView(). The rows for the end panel, in this order.
export function summaryRows(view) {
  const { stats } = view;
  const kills = Object.values(stats.kills).reduce((sum, n) => sum + n, 0);
  return [
    { label: 'Score', value: view.score },
    { label: 'Depth reached', value: stats.deepest },
    { label: 'Turns', value: view.hud.turn },
    { label: 'Kills', value: kills },
    { label: 'Items used', value: stats.itemsUsed },
    { label: 'Traps triggered', value: stats.trapsTriggered },
    { label: 'Damage taken', value: stats.damageTaken },
  ];
}
