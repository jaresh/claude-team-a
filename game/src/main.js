import { newGame, act, getView } from './core/game.js';
import { render } from './ui/render.js';
import { bindInput } from './ui/input.js';

const canvas = document.getElementById('screen');
const hudEl = document.getElementById('hud');
const logEl = document.getElementById('log');

function seedFromUrl() {
  const raw = new URLSearchParams(location.search).get('seed');
  if (raw !== null && raw.trim() !== '') return /^\d+$/.test(raw) ? Number(raw) : raw;
  return randomSeed();
}

function randomSeed() {
  return Math.floor(Math.random() * 1e9);
}

const helpEl = document.getElementById('help');

let state = newGame(seedFromUrl());

function draw() {
  render(canvas, getView(state), hudEl, logEl);
}

// Help is UI only: it never reaches act(), so the game state does not change.
function setHelp(open) {
  helpEl.hidden = !open;
}

bindInput(document, (action) => {
  if (action.type === 'help') {
    setHelp(helpEl.hidden);
  } else if (action.type === 'close') {
    setHelp(false);
  } else if (action.type === 'new') {
    state = newGame(randomSeed());
  } else {
    state = act(state, action);
  }
  draw();
});

window.addEventListener('resize', draw);
draw();
