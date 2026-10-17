// Score of a run from its stats. Pure: no DOM, no Math.random.

// Deeper levels, kills, items used and a win count for the score. Traps triggered count against it.
// Never below 0.
export function score(stats, status) {
  const kills = Object.values(stats.kills).reduce((sum, n) => sum + n, 0);
  const raw = 100 * stats.deepest + 10 * kills + 5 * stats.itemsUsed - 2 * stats.trapsTriggered
    + (status === 'won' ? 500 : 0);
  return Math.max(0, raw);
}
