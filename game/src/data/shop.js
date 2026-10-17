// Shop table. Append new rows at the end (rule 14). Each level's shop sells the rows with minDepth <= depth,
// in table order. effect: 'heal' (+amount hp, capped at maxHp), 'atk' or 'def' (+amount, permanent).
export const SHOP_STOCK = [
  { kind: 'potion', glyph: '!', color: '#ff5fa2', effect: 'heal', amount: 12, price: 10, minDepth: 1 },
  { kind: 'whetstone', glyph: '/', color: '#c8d3e0', effect: 'atk', amount: 1, price: 15, minDepth: 1 },
  { kind: 'ring', glyph: '=', color: '#e6c35c', effect: 'def', amount: 1, price: 25, minDepth: 2 },
  { kind: 'great potion', glyph: '!', color: '#ff2d6f', effect: 'heal', amount: 16, price: 30, minDepth: 4 },
];

// Gold a monster drops when the player kills it. Deterministic: no rng.
export function goldFor(monsterRow, depth) {
  return Math.max(1, monsterRow.xp) * 2 + depth;
}
