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

let state = newGame(seedFromUrl());

function draw() {
  render(canvas, getView(state), hudEl, logEl);
}

bindInput(document, (action) => {
  if (action.type === 'new') {
    state = newGame(randomSeed());
  } else {
    state = act(state, action);
  }
  draw();
});

window.addEventListener('resize', draw);
draw();
