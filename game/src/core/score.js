// Run score from the stats kept in the game state. Pure: no DOM, no Math.random.

const PER_DEPTH = 100, PER_KILL = 10, PER_ITEM = 5, PER_TRAP = -2, WIN_BONUS = 500;

// Integer, never below 0.
export function score(stats, status) {
  const kills = Object.values(stats.kills).reduce((sum, n) => sum + n, 0);
  const total = PER_DEPTH * stats.deepest + PER_KILL * kills + PER_ITEM * stats.itemsUsed
    + PER_TRAP * stats.trapsTriggered + (status === 'won' ? WIN_BONUS : 0);
  return Math.max(0, total);
}
