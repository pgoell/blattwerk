// Whether one place of a plus or minus task crosses (#838). Place 0 is the Einer.
// Plus: the two digits sum to more than 10. A sum of 10 (7 + 3, 17 + 23) does not. Nothing carries on.
// Minus: the first number's digit is smaller than the second's, so it would go below 0.

export function crossesAt(op: "+" | "-", a: number, b: number, place: number): boolean {
  const da = Math.floor(a / 10 ** place) % 10;
  const db = Math.floor(b / 10 ** place) % 10;
  return op === "+" ? da + db > 10 : da < db;
}
