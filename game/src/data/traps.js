// Trap table. Append new kinds at the end (rule 14).
// effect: 'damage' (-amount hp, never below 1), 'poison' (amount turns of poison) or 'teleport'
// (moves the player to a random free floor tile; amount is unused).
export const TRAPS = [
  { kind: 'spike', glyph: '^', color: '#c9d1d9', effect: 'damage', amount: 2, minDepth: 1 },
  { kind: 'poison needle', glyph: '*', color: '#84cc16', effect: 'poison', amount: 3, minDepth: 2 },
  { kind: 'teleport', glyph: '~', color: '#a78bfa', effect: 'teleport', amount: 0, minDepth: 3 },
];
