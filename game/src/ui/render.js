// Draws a View onto a canvas and fills the HUD, log and inventory elements.
// DOM is touched only inside render(), never at import time.

import { MIN_CELL, cameraWindow } from './camera.js';
import { endMessage, hpColor } from './hud.js';
import { legendRows, poisonLabel } from './legend.js';

const BG = '#0b0d12';
const MAX_ROWS = 15; // map rows on screen; the camera follows the player past this

export function render(canvas, view, hudEl, logEl) {
  const ctx = canvas.getContext('2d');
  const parentW = canvas.parentElement ? canvas.parentElement.clientWidth : 0;
  const avail = parentW > 0 ? parentW : (window.innerWidth || 360) - 32;

  const cols = Math.max(1, Math.min(view.w, Math.floor(avail / MIN_CELL)));
  const cellW = Math.floor(avail / cols);
  const rows = Math.min(view.h, MAX_ROWS);
  const win = cameraWindow(view, cols, rows);
  const cellH = cellW * 1.6;
  const cssW = cellW * win.cols;
  const cssH = cellH * win.rows;
  const dpr = window.devicePixelRatio || 1;
  const fontPx = Math.min(cellH * 0.85, (cellW / 0.6) * 0.9);

  canvas.dataset.cell = cellW;
  canvas.dataset.cols = win.cols;
  canvas.dataset.rows = win.rows;
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

  for (let row = 0; row < win.rows; row++) {
    for (let col = 0; col < win.cols; col++) {
      const tile = view.cells[(win.y0 + row) * view.w + win.x0 + col];
      if (!tile) continue;
      const px = col * cellW;
      const py = row * cellH;
      if (tile.bg) {
        ctx.fillStyle = tile.bg;
        ctx.fillRect(px, py, cellW, cellH);
      }
      if (tile.ch && tile.ch !== ' ') {
        ctx.fillStyle = tile.fg || '#e5e7eb';
        ctx.fillText(tile.ch, px + cellW / 2, py + cellH / 2);
      }
    }
  }

  const h = view.hud;
  const suffix = view.status === 'playing' ? '' : `  ${view.status.toUpperCase()}`;
  const poison = poisonLabel(view);
  hudEl.textContent =
    `HP ${h.hp}/${h.maxHp}  ATK ${h.atk}  DEF ${h.def}  LV ${h.level}  XP ${h.xp}  ` +
    `DEPTH ${h.depth}  TURN ${h.turn}${suffix}${poison === null ? '' : `  ${poison}`}`;

  renderHpBar(document.getElementById('hpbar'), h.hp, h.maxHp);
  renderEnd(document.getElementById('end'), view);
  renderLegend(document.getElementById('legend'), view);

  logEl.textContent = '';
  for (const line of view.log) {
    const li = document.createElement('li');
    li.textContent = line;
    logEl.appendChild(li);
  }

  renderInventory(document.getElementById('inventory'), view.inventory);
}

// The bar's inner .fill is hp / maxHp wide, coloured by hpColor.
function renderHpBar(barEl, hp, maxHp) {
  if (!barEl) return;
  const fill = barEl.querySelector('.fill');
  const frac = Math.max(0, Math.min(1, hp / maxHp));
  fill.style.width = `${frac * 100}%`;
  fill.style.background = hpColor(hp, maxHp);
}

// The end panel shows while the game is over; the New game button in it is a plain data-action.
function renderEnd(endEl, view) {
  if (!endEl) return;
  const msg = endMessage(view);
  endEl.hidden = msg === null;
  if (msg !== null) endEl.querySelector('.end-text').textContent = msg;
}

// One line per monster in sight, in the monster's colour. The list is empty when none are seen.
function renderLegend(legendEl, view) {
  if (!legendEl) return;
  legendEl.textContent = '';
  for (const row of legendRows(view)) {
    const li = document.createElement('li');
    li.style.color = row.color;
    li.textContent = row.text;
    legendEl.appendChild(li);
  }
}

// One button per item; a tap sends { type: 'use', index } through input.js.
function renderInventory(invEl, inventory) {
  if (!invEl) return;
  invEl.textContent = '';
  if (!inventory || inventory.length === 0) {
    const empty = document.createElement('span');
    empty.className = 'empty';
    empty.textContent = 'Inventory empty';
    invEl.appendChild(empty);
    return;
  }
  inventory.forEach((item, i) => {
    const btn = document.createElement('button');
    btn.className = 'small';
    btn.dataset.action = 'use';
    btn.dataset.index = String(i);
    btn.textContent = `${i + 1} ${item.glyph} ${item.kind}`;
    invEl.appendChild(btn);
  });
}
