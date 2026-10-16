// Draws a View onto a canvas and fills the HUD and log elements.
// DOM is touched only inside render(), never at import time.

const BG = '#0b0d12';
const MAX_CELL_W = 24; // css px; keeps small maps from getting huge on desktop

export function render(canvas, view, hudEl, logEl) {
  const ctx = canvas.getContext('2d');
  const parentW = canvas.parentElement ? canvas.parentElement.clientWidth : 0;
  const avail = parentW > 0 ? parentW : (window.innerWidth || 360) - 32;

  const cellW = Math.min(MAX_CELL_W, avail / view.w);
  const cellH = cellW * 1.6;
  const cssW = cellW * view.w;
  const cssH = cellH * view.h;
  const dpr = window.devicePixelRatio || 1;
  const fontPx = Math.min(cellH * 0.85, (cellW / 0.6) * 0.9);

  canvas.width = Math.round(cssW * dpr);
  canvas.height = Math.round(cssH * dpr);
  canvas.style.width = `${cssW}px`;
  canvas.style.height = `${cssH}px`;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

  ctx.fillStyle = BG;
  ctx.fillRect(0, 0, cssW, cssH);
  ctx.font = `${fontPx}px ui-monospace, Menlo, Consolas, "Courier New", monospace`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';

  for (let i = 0; i < view.w * view.h; i++) {
    const cell = view.cells[i];
    if (!cell) continue;
    const px = (i % view.w) * cellW;
    const py = Math.floor(i / view.w) * cellH;
    if (cell.bg) {
      ctx.fillStyle = cell.bg;
      ctx.fillRect(px, py, cellW, cellH);
    }
    if (cell.ch && cell.ch !== ' ') {
      ctx.fillStyle = cell.fg || '#e5e7eb';
      ctx.fillText(cell.ch, px + cellW / 2, py + cellH / 2);
    }
  }

  const h = view.hud;
  const suffix = view.status === 'playing' ? '' : `  ${view.status.toUpperCase()}`;
  hudEl.textContent =
    `HP ${h.hp}/${h.maxHp}  ATK ${h.atk}  DEF ${h.def}  LV ${h.level}  XP ${h.xp}  ` +
    `DEPTH ${h.depth}  TURN ${h.turn}${suffix}`;

  logEl.textContent = '';
  for (const line of view.log) {
    const li = document.createElement('li');
    li.textContent = line;
    logEl.appendChild(li);
  }
}
