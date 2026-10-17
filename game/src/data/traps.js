// Trap table. Append new kinds at the end (rule 14).
// effect: 'damage' (-amount hp, never below 1), 'poison' (poisons the player) or 'teleport'
// (moves the player to a random free floor tile). amount is used by 'damage' only.
export const TRAPS = [
  { kind: 'spike', glyph: '^', color: '#c9d1d9', effect: 'damage', amount: 2, minDepth: 1 },
  { kind: 'needle', glyph: '~', color: '#8ccf7e', effect: 'poison', amount: 0, minDepth: 2 },
  { kind: 'rune', glyph: '*', color: '#a78bfa', effect: 'teleport', amount: 0, minDepth: 3 },
];
