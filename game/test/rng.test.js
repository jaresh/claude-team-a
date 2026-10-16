import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createRng } from '../src/core/rng.js';

test('same seed gives the same sequence', () => {
  const a = createRng(42), b = createRng(42);
  for (let i = 0; i < 200; i++) assert.equal(a.next(), b.next());
});

test('next() stays in [0, 1)', () => {
  const r = createRng(7);
  for (let i = 0; i < 5000; i++) {
    const v = r.next();
    assert.ok(v >= 0 && v < 1, `out of range: ${v}`);
  }
});

test('createRng(rng.state()) continues the sequence', () => {
  const r = createRng(1234);
  for (let i = 0; i < 50; i++) r.next();
  const copy = createRng(r.state());
  for (let i = 0; i < 200; i++) assert.equal(copy.next(), r.next());
});

test('int() stays inside inclusive bounds and hits both ends', () => {
  const r = createRng(99);
  const seen = new Set();
  for (let i = 0; i < 10000; i++) {
    const v = r.int(3, 7);
    assert.ok(Number.isInteger(v));
    assert.ok(v >= 3 && v <= 7, `out of bounds: ${v}`);
    seen.add(v);
  }
  assert.deepEqual([...seen].sort(), [3, 4, 5, 6, 7]);
});

test('pick() returns an element of the array', () => {
  const r = createRng(5);
  const list = ['a', 'b', 'c'];
  for (let i = 0; i < 200; i++) assert.ok(list.includes(r.pick(list)));
});
