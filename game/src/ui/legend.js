// Pure helpers for the monster legend and the poison label. No DOM here, so node tests load it
// directly. render.js calls these and does the DOM work.

// view: a View from getView(). One row per visibleMonsters entry, in that entry's colour.
export function legendRows(view) {
  return view.visibleMonsters.map((m) => {
    const ability = m.ability ? ` ${m.ability}` : '';
    return { text: `${m.glyph} ${m.kind} ${m.hp}/${m.maxHp}${ability}`, color: m.color };
  });
}

// view: a View from getView(). Returns the poison label while poisoned, null otherwise.
export function poisonLabel(view) {
  const turns = view.hud.poison;
  return turns > 0 ? `Poisoned (${turns})` : null;
}
