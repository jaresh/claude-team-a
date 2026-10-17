// Trap table. Append new kinds at the end (rule 14).
// effect: 'damage' (-amount hp, never below 1), 'poison' (POISON_TURNS of poison) or
// 'teleport' (a random free floor tile). Traps start hidden; the player reveals them by stepping on them.
export const TRAPS = [
  { kind: 'spike', glyph: '^', color: '#c9d1d9', effect: 'damage', amount: 1, minDepth: 1 },
  { kind: 'poison needle', glyph: '*', color: '#84cc16', effect: 'poison', amount: 0, minDepth: 5 },
  { kind: 'teleport', glyph: '~', color: '#c084fc', effect: 'teleport', amount: 0, minDepth: 4 },
];
