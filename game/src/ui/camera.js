// Camera: the part of the map that render() draws, centred on the player.
// Pure: no DOM, so it is tested with node alone.

export const MIN_CELL = 16; // css px; a map cell never draws smaller than this

const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));

// view: { w, h, player: { x, y } }. cols and rows are the most that fit on screen.
// Returns the window { x0, y0, cols, rows } in map tiles.
export function cameraWindow(view, cols, rows) {
  const w = Math.min(cols, view.w);
  const h = Math.min(rows, view.h);
  const x0 = clamp(view.player.x - Math.floor(w / 2), 0, view.w - w);
  const y0 = clamp(view.player.y - Math.floor(h / 2), 0, view.h - h);
  return { x0, y0, cols: w, rows: h };
}
