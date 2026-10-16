// Camera: which part of the map the canvas shows, centred on the player.
// Pure: no DOM, so it loads and runs under node --test.

export const MIN_CELL = 16; // css px

const clamp = (v, lo, hi) => Math.max(lo, Math.min(v, hi));

// view: { w, h, player: { x, y } }. cols and rows are the most that fit on screen.
// Returns the window origin and its size, never larger than the map.
export function cameraWindow(view, cols, rows) {
  const w = Math.min(cols, view.w);
  const h = Math.min(rows, view.h);
  const x0 = clamp(view.player.x - Math.floor(w / 2), 0, view.w - w);
  const y0 = clamp(view.player.y - Math.floor(h / 2), 0, view.h - h);
  return { x0, y0, cols: w, rows: h };
}
