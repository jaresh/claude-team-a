// Keyboard and on-screen button input. Turns keys and buttons into actions and calls onAction.
// DOM is touched only inside bindInput(), never at import time.

const MOVES = {
  ArrowUp: [0, -1], ArrowDown: [0, 1], ArrowLeft: [-1, 0], ArrowRight: [1, 0],
  w: [0, -1], s: [0, 1], a: [-1, 0], d: [1, 0],
  k: [0, -1], j: [0, 1], h: [-1, 0], l: [1, 0],
  y: [-1, -1], u: [1, -1], b: [-1, 1], n: [1, 1],
};

// Pure: key string (KeyboardEvent.key) -> action object, or null.
export function keyToAction(key) {
  if (typeof key !== 'string' || key === '') return null;
  const k = key.length === 1 ? key.toLowerCase() : key;
  if (MOVES[k]) {
    const [dx, dy] = MOVES[k];
    return { type: 'move', dx, dy };
  }
  if (k === '.') return { type: 'wait' };
  if (k === 'g') return { type: 'pickup' };
  if (k === '>') return { type: 'descend' };
  if (/^[1-9]$/.test(k)) return { type: 'use', index: Number(k) - 1 };
  if (k === '?') return { type: 'help' };
  if (k === 'Escape') return { type: 'close' };
  return null;
}

// Pure: button dataset ({ action, dx, dy, index }) -> action object, or null.
export function buttonToAction(ds) {
  switch (ds.action) {
    case 'move': return { type: 'move', dx: Number(ds.dx), dy: Number(ds.dy) };
    case 'wait': return { type: 'wait' };
    case 'pickup': return { type: 'pickup' };
    case 'descend': return { type: 'descend' };
    case 'use':
    case 'buy': {
      // Inventory and shop buttons carry data-index; a missing or bad index is not an action.
      const index = Number(ds.index);
      return ds.index && Number.isInteger(index) ? { type: ds.action, index } : null;
    }
    case 'new': return { type: 'new' };
    case 'help': return { type: 'help' };
    default: return null;
  }
}

function isEditable(el) {
  if (!el || !el.tagName) return false;
  return el.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(el.tagName);
}

// root: document (or an element). Buttons are any [data-action] inside root, including the
// inventory and shop buttons that render() adds, so taps on them reach onAction through the same handler.
// Returns an unbind function.
export function bindInput(root, onAction) {
  const onKey = (e) => {
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    if (isEditable(e.target)) return;
    const action = keyToAction(e.key);
    if (!action) return;
    e.preventDefault();
    onAction(action);
  };
  const onClick = (e) => {
    const target = e.target;
    const btn = target && target.closest ? target.closest('[data-action]') : null;
    if (!btn || !root.contains(btn)) return;
    const action = buttonToAction(btn.dataset);
    if (action) onAction(action);
  };
  root.addEventListener('keydown', onKey);
  root.addEventListener('click', onClick);
  return () => {
    root.removeEventListener('keydown', onKey);
    root.removeEventListener('click', onClick);
  };
}
