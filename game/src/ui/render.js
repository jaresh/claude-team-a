// Draws a View onto a canvas and fills the HUD, log and inventory elements.
// DOM is touched only inside render(), never at import time.

import { MIN_CELL, cameraWindow } from './camera.js';
import { endMessage, hpColor } from './hud.js';
import { legendRows, poisonLabel } from './legend.js';
import { HELP_KEYS, glyphRows } from './help.js';
import { summaryRows } from './scores.js';

const BG = '#0b0d12';
const MAX_ROWS = 15; // map rows on screen; the camera follows the player past this

// scores: the saved high-score list (see scores.js), shown in the end panel once the game is over.
export function render(canvas, view, hudEl, logEl, scores = []) {
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
    `HP ${h.hp}/${h.maxHp}  ATK ${h.atk}  DEF ${h.def}  LV ${h.level}  XP ${h.xp}  GOLD ${h.gold}  ` +
    `DEPTH ${h.depth}  TURN ${h.turn}${suffix}${poison === null ? '' : `  ${poison}`}`;

  renderHpBar(document.getElementById('hpbar'), h.hp, h.maxHp);
  renderEnd(document.getElementById('end'), view, scores);
  renderLegend(document.getElementById('legend'), view);
  renderHelp(document.getElementById('help'), view);

  logEl.textContent = '';
  for (const line of view.log) {
    const li = document.createElement('li');
    li.textContent = line;
    logEl.appendChild(li);
  }

  renderInventory(document.getElementById('inventory'), view.inventory);
  renderShop(document.getElementById('shop'), view.shop);
}

// Pure: the shop buttons for a view.shop. Empty unless the player stands on the shop tile.
// Each row's index is the one a buy action takes (an index into the current stock).
export function shopRows(shop) {
  if (!shop || !shop.open) return [];
  return shop.stock.map((s) => ({ index: s.index, text: `${s.glyph} ${s.kind} ${s.price}g` }));
}

// The bar's inner .fill is hp / maxHp wide, coloured by hpColor.
function renderHpBar(barEl, hp, maxHp) {
  if (!barEl) return;
  const fill = barEl.querySelector('.fill');
  const frac = Math.max(0, Math.min(1, hp / maxHp));
  fill.style.width = `${frac * 100}%`;
  fill.style.background = hpColor(hp, maxHp);
}

// The end panel shows while the game is over: the message, the run summary, then the high scores.
// The New game button in it is a plain data-action.
function renderEnd(endEl, view, scores) {
  if (!endEl) return;
  const msg = endMessage(view);
  endEl.hidden = msg === null;
  if (msg === null) return;
  endEl.querySelector('.end-text').textContent = msg;
  fillList(document.getElementById('summary'), summaryRows(view).map((r) => [r.label, r.value]));
  const rows = scores.map((e) => [
    `${e.score}`,
    `depth ${e.depth}, ${e.turns} turns${e.won ? ', won' : ''}`,
  ]);
  fillList(document.getElementById('scores'), rows.length > 0 ? rows : [['No high scores yet', '']]);
}

// One li per [left, right] pair; the right text is set apart by the list's flex layout.
function fillList(listEl, pairs) {
  if (!listEl) return;
  listEl.textContent = '';
  for (const [left, right] of pairs) {
    const li = document.createElement('li');
    const a = document.createElement('span');
    a.textContent = left;
    const b = document.createElement('span');
    b.textContent = right;
    li.append(a, b);
    listEl.appendChild(li);
  }
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

// The help panel: one line per HELP_KEYS entry, then one per glyph row in that row's colour.
function renderHelp(helpEl, view) {
  if (!helpEl) return;
  helpEl.textContent = '';
  const addLine = (text, color) => {
    const li = document.createElement('li');
    if (color) li.style.color = color;
    li.textContent = text;
    helpEl.appendChild(li);
  };
  for (const row of HELP_KEYS) addLine(`${row.keys}  ${row.action}`);
  for (const row of glyphRows(view)) addLine(`${row.glyph} ${row.name}`, row.color);
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

// The shop panel is shown only while the player stands on the shop tile; a tap on a row sends
// { type: 'buy', index } through input.js.
function renderShop(shopEl, shop) {
  if (!shopEl) return;
  shopEl.hidden = !(shop && shop.open);
  shopEl.textContent = '';
  if (shopEl.hidden) return;
  const title = document.createElement('span');
  title.className = 'title';
  title.textContent = 'Shop';
  shopEl.appendChild(title);
  const rows = shopRows(shop);
  if (rows.length === 0) {
    const empty = document.createElement('span');
    empty.className = 'empty';
    empty.textContent = 'Nothing for sale';
    shopEl.appendChild(empty);
    return;
  }
  for (const row of rows) {
    const btn = document.createElement('button');
    btn.className = 'small';
    btn.dataset.action = 'buy';
    btn.dataset.index = String(row.index);
    btn.textContent = row.text;
    shopEl.appendChild(btn);
  }
}
