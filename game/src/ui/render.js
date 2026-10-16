// Draws the camera window of a View onto a canvas, and fills the inventory panel,
// the HUD and the log. DOM is touched only inside render(), never at import time.

import { MIN_CELL, cameraWindow } from './camera.js';

const BG = '#0b0d12';
const MAX_ROWS = 15;
const CELL_ASPECT = 1.6; // cell height / cell width

// Pure: view and canvas width (css px) -> the grid the canvas uses.
// cols: how many map columns fit at MIN_CELL or more; cell: width of one cell in css px.
export function layout(view, cssWidth) {
  const width = Math.max(1, cssWidth);
  const cols = Math.max(1, Math.min(view.w, Math.floor(width / MIN_CELL)));
  const cell = Math.floor(width / cols);
  const rows = Math.min(view.h, MAX_ROWS);
  return { cols, rows, cell, cellH: cell * CELL_ASPECT };
}

export function render(canvas, view, hudEl, logEl) {
  const ctx = canvas.getContext('2d');
  const parentW = canvas.parentElement ? canvas.parentElement.clientWidth : 0;
  const cssWidth = parentW > 0 ? parentW : (window.innerWidth || 360) - 32;

  const grid = layout(view, cssWidth);
  const win = cameraWindow(view, grid.cols, grid.rows);
  const { cell, cellH } = grid;
  const cssW = win.cols * cell;
  const cssH = win.rows * cellH;
  const dpr = window.devicePixelRatio || 1;
  const fontPx = Math.min(cellH * 0.85, (cell / 0.6) * 0.9);

  canvas.width = Math.round(cssW * dpr);
  canvas.height = Math.round(cssH * dpr);
  canvas.style.width = `${cssW}px`;
  canvas.style.height = `${cssH}px`;
  canvas.dataset.cell = String(cell);
  canvas.dataset.cols = String(win.cols);
  canvas.dataset.rows = String(win.rows);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

  ctx.fillStyle = BG;
  ctx.fillRect(0, 0, cssW, cssH);
  ctx.font = `${fontPx}px ui-monospace, Menlo, Consolas, "Courier New", monospace`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';

  for (let r = 0; r < win.rows; r++) {
    for (let c = 0; c < win.cols; c++) {
      const tile = view.cells[(win.y0 + r) * view.w + (win.x0 + c)];
      if (!tile) continue;
      const px = c * cell;
      const py = r * cellH;
      if (tile.bg) {
        ctx.fillStyle = tile.bg;
        ctx.fillRect(px, py, cell, cellH);
      }
      if (tile.ch && tile.ch !== ' ') {
        ctx.fillStyle = tile.fg || '#e5e7eb';
        ctx.fillText(tile.ch, px + cell / 2, py + cellH / 2);
      }
    }
  }

  renderInventory(view);

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

// One button per item (data-action="use", data-index = slot), or the empty note.
function renderInventory(view) {
  const panel = document.getElementById('inventory');
  if (!panel) return;
  panel.textContent = '';
  const items = view.inventory || [];
  if (items.length === 0) {
    const note = document.createElement('p');
    note.className = 'hint';
    note.textContent = 'Inventory empty';
    panel.appendChild(note);
    return;
  }
  items.forEach((item, i) => {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'small';
    btn.dataset.action = 'use';
    btn.dataset.index = String(i);
    btn.textContent = `${i + 1} ${item.glyph} ${item.kind}`;
    if (item.color) btn.style.color = item.color;
    panel.appendChild(btn);
  });
}
