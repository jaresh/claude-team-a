// Pure helpers for the HUD: the end-of-game message and the HP bar colour.
// No DOM here; render.js does the drawing.

// view.status 'playing' -> null; 'dead' or 'won' -> the message for the end panel.
export function endMessage(view) {
  const { depth, turn } = view.hud;
  if (view.status === 'dead') return `You died on depth ${depth} after ${turn} turns.`;
  if (view.status === 'won') return `You won! Depth ${depth} in ${turn} turns.`;
  return null;
}

// Green above half health, amber above a quarter, red below.
export function hpColor(hp, maxHp) {
  const ratio = hp / maxHp;
  if (ratio > 0.5) return '#3fb950';
  if (ratio > 0.25) return '#d29922';
  return '#f85149';
}
