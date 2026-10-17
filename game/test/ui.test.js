import { test } from 'node:test';
import assert from 'node:assert/strict';
import { newGame, act, getView, MAX_DEPTH } from '../src/ui/mock-game.js';
import { render } from '../src/ui/render.js';
import { bindInput, keyToAction, buttonToAction } from '../src/ui/input.js';

function assertViewShape(view) {
  assert.equal(typeof view.w, 'number');
  assert.equal(typeof view.h, 'number');
  assert.equal(view.cells.length, view.w * view.h);
  for (const c of view.cells) {
    assert.equal(typeof c.ch, 'string');
    assert.equal(c.ch.length, 1);
    assert.equal(typeof c.fg, 'string');
    assert.ok(c.bg === null || typeof c.bg === 'string');
  }
  for (const field of ['hp', 'maxHp', 'atk', 'def', 'depth', 'level', 'xp', 'turn']) {
    assert.equal(typeof view.hud[field], 'number', `hud.${field}`);
  }
  assert.ok(Array.isArray(view.log));
  assert.ok(view.log.length <= 5, 'log has at most 5 lines');
  for (const line of view.log) assert.equal(typeof line, 'string');
  assert.ok(['playing', 'dead', 'won'].includes(view.status));
}

test('newGame returns a playing state at turn 0', () => {
  const state = newGame(42);
  assert.equal(state.status, 'playing');
  assert.equal(state.turn, 0);
  assert.equal(state.depth, 1);
  assert.ok(state.visible instanceof Set);
  assert.equal(state.explored.length, state.map.w * state.map.h);
});

test('getView returns the contract shape', () => {
  assertViewShape(getView(newGame(7)));
});

test('a walkable move changes position and advances the turn', () => {
  const state = newGame(1);
  const { x, y } = state.player;
  act(state, { type: 'move', dx: 1, dy: 0 });
  assert.equal(state.player.x, x + 1);
  assert.equal(state.player.y, y);
  assert.equal(state.turn, 1);
});

test('a move into a wall costs no turn and logs a line', () => {
  const state = newGame(1);
  state.player.x = 1;
  state.player.y = 1;
  act(state, { type: 'move', dx: -1, dy: 0 });
  assert.equal(state.player.x, 1);
  assert.equal(state.turn, 0);
  assert.match(state.log[state.log.length - 1], /wall/);
});

test('many actions keep the view valid and every action logs a line', () => {
  const state = newGame(3);
  const actions = [
    { type: 'move', dx: 1, dy: 0 }, { type: 'move', dx: 0, dy: 1 },
    { type: 'wait' }, { type: 'pickup' }, { type: 'use', index: 0 },
    { type: 'move', dx: -1, dy: -1 }, { type: 'descend' },
  ];
  for (let i = 0; i < 200 && state.status === 'playing'; i++) {
    state.log = [];
    act(state, actions[i % actions.length]);
    assert.ok(state.log.length >= 1, `action ${i} logged a line`);
    assertViewShape(getView(state));
  }
});

test('act ignores actions once the game is over', () => {
  const state = newGame(5);
  state.status = 'dead';
  const turn = state.turn;
  act(state, { type: 'wait' });
  assert.equal(state.turn, turn);
  assert.equal(state.status, 'dead');
});

test('descend off the stairs does nothing', () => {
  const state = newGame(5);
  act(state, { type: 'descend' });
  assert.equal(state.depth, 1);
  assert.equal(state.turn, 0);
});

test('descend on the stairs goes down a level, and wins on the last depth', () => {
  const state = newGame(5);
  state.player.x = state.map.stairs.x;
  state.player.y = state.map.stairs.y;
  act(state, { type: 'descend' });
  assert.equal(state.depth, 2);
  assert.equal(state.status, 'playing');

  state.depth = MAX_DEPTH;
  state.player.x = state.map.stairs.x;
  state.player.y = state.map.stairs.y;
  act(state, { type: 'descend' });
  assert.equal(state.status, 'won');
});

test('keyToAction maps the contract keys', () => {
  assert.deepEqual(keyToAction('ArrowUp'), { type: 'move', dx: 0, dy: -1 });
  assert.deepEqual(keyToAction('a'), { type: 'move', dx: -1, dy: 0 });
  assert.deepEqual(keyToAction('D'), { type: 'move', dx: 1, dy: 0 });
  assert.deepEqual(keyToAction('y'), { type: 'move', dx: -1, dy: -1 });
  assert.deepEqual(keyToAction('n'), { type: 'move', dx: 1, dy: 1 });
  assert.deepEqual(keyToAction('.'), { type: 'wait' });
  assert.deepEqual(keyToAction('g'), { type: 'pickup' });
  assert.deepEqual(keyToAction('>'), { type: 'descend' });
  assert.deepEqual(keyToAction('3'), { type: 'use', index: 2 });
  assert.equal(keyToAction('x'), null);
  assert.equal(keyToAction('0'), null);
  assert.deepEqual(keyToAction('?'), { type: 'help' });
  assert.deepEqual(keyToAction('Escape'), { type: 'close' });
});

test('buttonToAction maps the on-screen buttons', () => {
  assert.deepEqual(buttonToAction({ action: 'move', dx: '0', dy: '-1' }), { type: 'move', dx: 0, dy: -1 });
  assert.deepEqual(buttonToAction({ action: 'wait' }), { type: 'wait' });
  assert.deepEqual(buttonToAction({ action: 'use', index: '0' }), { type: 'use', index: 0 });
  assert.deepEqual(buttonToAction({ action: 'new' }), { type: 'new' });
  assert.deepEqual(buttonToAction({ action: 'help' }), { type: 'help' });
  assert.deepEqual(buttonToAction({ action: 'close' }), { type: 'close' });
  assert.equal(buttonToAction({}), null);
});

test('render and input modules load without a DOM', () => {
  assert.equal(typeof render, 'function');
  assert.equal(typeof bindInput, 'function');
});
