// Pure helpers for the end screen and the HP bar. No DOM here, so node tests load it directly.
// render.js calls these and does the DOM work.

// view: a View from getView(). Returns the end-of-game text, or null while the game is playing.
export function endMessage(view) {
  if (view.status === 'dead') {
    return `You died on depth ${view.hud.depth} after ${view.hud.turn} turns.`;
  }
  if (view.status === 'won') {
    return `You won! Depth ${view.hud.depth} in ${view.hud.turn} turns.`;
  }
  return null;
}

// Colour of the HP bar: green above half, amber above a quarter, red at or below a quarter.
export function hpColor(hp, maxHp) {
  const frac = hp / maxHp;
  if (frac > 0.5) return '#3fb950';
  if (frac > 0.25) return '#d29922';
  return '#f85149';
}
