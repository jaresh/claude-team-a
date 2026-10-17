// Trap table. Append new kinds at the end (rule 14).
// effect: 'damage' (-amount hp, never below 1), 'poison' (3 turns of poison) or 'teleport' (moves
// the player to a random free floor tile). A trap is hidden until the player steps on it.
export const TRAPS = [
  { kind: 'spike', glyph: '^', color: '#c9d1d9', effect: 'damage', amount: 2, minDepth: 1 },
  { kind: 'poison needle', glyph: '*', color: '#7fa650', effect: 'poison', amount: 0, minDepth: 2 },
  { kind: 'teleport', glyph: '~', color: '#9d8fd6', effect: 'teleport', amount: 0, minDepth: 2 },
];
