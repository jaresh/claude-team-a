// Camera window: which part of the map the canvas shows, centred on the player.
// Pure: no DOM, no randomness.

export const MIN_CELL = 16; // css px, the smallest cell that stays readable on a phone

// view: { w, h, player: { x, y } }; cols, rows: the window size wanted.
// -> { x0, y0, cols, rows }. The window never exceeds the map.
export function cameraWindow(view, cols, rows) {
  const c = Math.min(cols, view.w);
  const r = Math.min(rows, view.h);
  // Without a player (should not happen), centre on the map.
  const px = view.player ? view.player.x : Math.floor(view.w / 2);
  const py = view.player ? view.player.y : Math.floor(view.h / 2);
  const x0 = clamp(px - Math.floor(c / 2), 0, view.w - c);
  const y0 = clamp(py - Math.floor(r / 2), 0, view.h - r);
  return { x0, y0, cols: c, rows: r };
}

function clamp(v, lo, hi) {
  return Math.max(lo, Math.min(hi, v));
}
