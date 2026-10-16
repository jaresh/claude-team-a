// Seeded pseudo-random generator (mulberry32). No Math.random anywhere in core.

export function createRng(seed) {
  let s = seed >>> 0;

  function next() {
    s = (s + 0x6d2b79f5) >>> 0;
    let t = s;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  }

  return {
    next,
    int(min, max) {
      return Math.floor(next() * (max - min + 1)) + min;
    },
    pick(array) {
      return array[Math.floor(next() * array.length)];
    },
    state() {
      return s;
    },
  };
}
