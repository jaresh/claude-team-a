// Draws the camera window of a View onto a canvas, and fills the HUD, log and inventory elements.
// DOM is touched only inside render(), never at import time.

import { cameraWindow, MIN_CELL } from './camera.js';

const BG = '#0b0d12';
const MAX_ROWS = 15;

export function render(canvas, view, hudEl, logEl) {
  const ctx = canvas.getContext('2d');
  const parentW = canvas.parentElement ? canvas.parentElement.clientWidth : 0;
  const avail = parentW > 0 ? parentW : (window.innerWidth || 360) - 32;

  const fit = Math.max(1, Math.floor(avail / MIN_CELL));
  const win = cameraWindow(view, Math.min(view.w, fit), Math.min(view.h, MAX_ROWS));
  const cellW = Math.floor(avail / win.cols);
  const cellH = cellW * 1.6;
  const cssW = cellW * win.cols;
  const cssH = cellH * win.rows;
  const dpr = window.devicePixelRatio || 1;
  const fontPx = Math.min(cellH * 0.85, (cellW / 0.6) * 0.9);

  canvas.dataset.cell = String(cellW);
  canvas.dataset.cols = String(win.cols);
  canvas.dataset.rows = String(win.rows);
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

  for (let r = 0; r < win.rows; r++) {
    for (let c = 0; c < win.cols; c++) {
      const cell = view.cells[(win.y0 + r) * view.w + win.x0 + c];
      if (!cell) continue;
      const px = c * cellW;
      const py = r * cellH;
      if (cell.bg) {
        ctx.fillStyle = cell.bg;
        ctx.fillRect(px, py, cellW, cellH);
      }
      if (cell.ch && cell.ch !== ' ') {
        ctx.fillStyle = cell.fg || '#e5e7eb';
        ctx.fillText(cell.ch, px + cellW / 2, py + cellH / 2);
      }
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

  renderInventory(view.inventory);
}

// One button per item; tapping it sends { type: 'use', index: i } through input.js.
function renderInventory(items) {
  const panel = document.getElementById('inventory');
  if (!panel) return;
  panel.textContent = '';
  if (items.length === 0) {
    const empty = document.createElement('p');
    empty.className = 'hint';
    empty.textContent = 'Inventory empty';
    panel.appendChild(empty);
    return;
  }
  items.forEach((item, i) => {
    const btn = document.createElement('button');
    btn.className = 'small';
    btn.dataset.action = 'use';
    btn.dataset.index = String(i);
    btn.textContent = `${i + 1} ${item.glyph} ${item.kind}`;
    panel.appendChild(btn);
  });
}
