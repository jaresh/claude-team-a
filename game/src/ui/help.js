// Pure helpers for the help panel: the key list and the glyph legend. No DOM here, so node tests
// load it directly. render.js calls these and does the DOM work.

export const HELP_KEYS = [
  { keys: 'Arrows, WASD, hjkl, yubn', action: 'move' },
  { keys: '.', action: 'wait' },
  { keys: 'g', action: 'pick up' },
  { keys: '>', action: 'descend' },
  { keys: '1-9', action: 'use item' },
  { keys: '?', action: 'help' },
  { keys: 'Esc', action: 'close help' },
];

// view: a View from getView(). You, then the stairs, then one row per trap kind in view.traps,
// in first-seen order. Colours match what getView draws.
export function glyphRows(view) {
  const rows = [
    { glyph: '@', color: '#f8fafc', name: 'you' },
    { glyph: '>', color: '#fde047', name: 'stairs down' },
  ];
  const seen = new Set();
  for (const t of view.traps) {
    if (seen.has(t.kind)) continue;
    seen.add(t.kind);
    rows.push({ glyph: t.glyph, color: t.color, name: `${t.kind} trap` });
  }
  return rows;
}
