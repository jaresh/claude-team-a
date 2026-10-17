import { newGame, act, getView } from './core/game.js';
import { render } from './ui/render.js';
import { bindInput } from './ui/input.js';
import { addScore, loadScores, saveScores } from './ui/scores.js';

const canvas = document.getElementById('screen');
const hudEl = document.getElementById('hud');
const logEl = document.getElementById('log');
const helpEl = document.getElementById('help');

function seedFromUrl() {
  const raw = new URLSearchParams(location.search).get('seed');
  if (raw !== null && raw.trim() !== '') return /^\d+$/.test(raw) ? Number(raw) : raw;
  return randomSeed();
}

function randomSeed() {
  return Math.floor(Math.random() * 1e9);
}

let state = newGame(seedFromUrl());
let recorded = false; // the current game has been added to the high scores
// Storage can be missing or blocked (private mode); the game works without high scores.
let scores = [];
try {
  scores = loadScores(localStorage);
} catch {
  scores = [];
}

function recordIfOver(view) {
  if (view.status === 'playing' || recorded) return;
  recorded = true;
  scores = addScore(scores, {
    score: view.score, depth: view.stats.deepest, turns: view.hud.turn, seed: state.seed, won: view.status === 'won',
  });
  try {
    saveScores(localStorage, scores);
  } catch {
    // not saved; the list still shows for this page
  }
}

function draw() {
  const view = getView(state);
  recordIfOver(view);
  render(canvas, view, hudEl, logEl, scores);
}

bindInput(document, (action) => {
  if (action.type === 'help') {
    helpEl.hidden = !helpEl.hidden;
    return;
  }
  if (action.type === 'close') {
    helpEl.hidden = true;
    return;
  }
  if (action.type === 'new') {
    state = newGame(randomSeed());
    recorded = false;
  } else {
    state = act(state, action);
  }
  draw();
});

window.addEventListener('resize', draw);
draw();
