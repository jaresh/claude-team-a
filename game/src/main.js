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

let seed, state, recorded;
let scores = readScores();

function startGame(newSeed) {
  seed = newSeed;
  state = newGame(seed);
  recorded = false;
}

// Each finished game goes into the high scores once. The seed is kept here: the view has none.
function recordIfEnded(view) {
  if (view.status === 'playing' || recorded) return;
  recorded = true;
  scores = addScore(scores, {
    score: view.score, depth: view.stats.deepest, turns: view.hud.turn, seed, won: view.status === 'won',
  });
  writeScores(scores);
}

// localStorage can be missing or throw (private mode, storage disabled); the game works without it.
function readScores() {
  try {
    return loadScores(window.localStorage);
  } catch {
    return [];
  }
}

function writeScores(list) {
  try {
    saveScores(window.localStorage, list);
  } catch {
    // the list still lasts for this page
  }
}

function draw() {
  const view = getView(state);
  recordIfEnded(view);
  render(canvas, view, hudEl, logEl, scores);
}

startGame(seedFromUrl());

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
    startGame(randomSeed());
  } else {
    state = act(state, action);
  }
  draw();
});

window.addEventListener('resize', draw);
draw();
