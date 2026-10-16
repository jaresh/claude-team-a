// Pure helpers for the monster legend and the poison label. No DOM here, so node tests load it
// directly. render.js calls these and does the DOM work.

// view: a View from getView(). One row per visible monster: { text, color }.
export function legendRows(view) {
  return view.visibleMonsters.map((m) => {
    const ability = m.ability ? ` ${m.ability}` : '';
    return { text: `${m.glyph} ${m.kind} ${m.hp}/${m.maxHp}${ability}`, color: m.color };
  });
}

// view: a View from getView(). Returns the poison label while poisoned, else null.
export function poisonLabel(view) {
  if (view.hud.poison > 0) return `Poisoned (${view.hud.poison})`;
  return null;
}
