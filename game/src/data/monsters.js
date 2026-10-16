// Monster table. Append new kinds at the end (rule 14).
// ability: null, 'regen' (heals 1 hp per turn), 'poison' (melee hits poison the player) or
// 'ranged' (shoots from 2 to 4 tiles away).
export const MONSTERS = [
  { kind: 'rat', glyph: 'r', color: '#b9a37e', hp: 3, atk: 1, def: 0, xp: 1, minDepth: 1, ability: null },
  { kind: 'kobold', glyph: 'k', color: '#7fa650', hp: 6, atk: 1, def: 1, xp: 3, minDepth: 2, ability: null },
  { kind: 'goblin', glyph: 'g', color: '#5fb3a1', hp: 8, atk: 1, def: 1, xp: 4, minDepth: 2, ability: 'poison' },
  { kind: 'bat', glyph: 'b', color: '#9d8fd6', hp: 5, atk: 2, def: 0, xp: 3, minDepth: 3, ability: null },
  { kind: 'orc', glyph: 'o', color: '#d9823b', hp: 8, atk: 2, def: 2, xp: 8, minDepth: 4, ability: 'regen' },
  { kind: 'troll', glyph: 'T', color: '#c2553b', hp: 20, atk: 6, def: 3, xp: 15, minDepth: 5, ability: null },
  { kind: 'archer', glyph: 'a', color: '#e0c050', hp: 5, atk: 3, def: 0, xp: 5, minDepth: 3, ability: 'ranged' },
];
