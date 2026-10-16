// Item table. Append new kinds at the end (rule 14).
// effect: 'heal' (+amount hp, capped at maxHp), 'atk' or 'def' (+amount, permanent).
export const ITEMS = [
  { kind: 'potion', glyph: '!', color: '#ff5fa2', effect: 'heal', amount: 8, minDepth: 1 },
  { kind: 'whetstone', glyph: '/', color: '#c8d3e0', effect: 'atk', amount: 1, minDepth: 1 },
  { kind: 'ring', glyph: '=', color: '#e6c35c', effect: 'def', amount: 1, minDepth: 2 },
  { kind: 'great potion', glyph: '!', color: '#ff2d6f', effect: 'heal', amount: 16, minDepth: 4 },
];
