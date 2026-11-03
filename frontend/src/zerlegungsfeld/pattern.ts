// A Zerlegungsfeld pattern: "X" is any digit, a digit is fixed, the length is the number of digits.
// With no pattern and with zero allowed, the second number is picked as before, so an old sheet keeps its tasks.

export function clean(raw: string | undefined): string {
  return (raw ?? "").toUpperCase().replace(/[^0-9X]/g, "").slice(0, 4);
}

export function matches(pattern: string, n: number, allowZero: boolean): boolean {
  if (n < 0) return false;
  const text = String(n);
  if (!allowZero && text.includes("0")) return false;
  if (!pattern) return true;
  if (text.length !== pattern.length) return false;
  for (let i = 0; i < pattern.length; i++) if (pattern[i] !== "X" && pattern[i] !== text[i]) return false;
  return true;
}

// The first numbers that have a second number, and the pick of that second number.
export function candidates(
  op: "+" | "-",
  max: number,
  u: number,
  g: number,
  pa: string,
  pb: string,
  zeroOk: boolean,
  bRange: (a: number) => [number, number] | null,
): { A: number[]; pickB: (a: number, next: () => number) => number } {
  const shaped = pa !== "" || pb !== "" || !zeroOk;
  const bsOf = (a: number): number[] => {
    const range = bRange(a);
    if (!range) return [];
    const out: number[] = [];
    for (let b = range[0]; b <= range[1]; b += g) if (matches(pb, b, zeroOk)) out.push(b);
    return out;
  };
  const pickB = (a: number, next: () => number) => {
    const range = bRange(a)!;
    if (!shaped) {
      const [lo, hi] = range;
      return lo + g * Math.floor(next() * ((hi - lo) / g + 1));
    }
    const bs = bsOf(a);
    return bs[Math.floor(next() * bs.length)];
  };
  const A: number[] = [];
  for (let a = g; a <= max; a += g) {
    if (a % u === 0 || (op === "-" && a < u)) continue;
    if (shaped ? matches(pa, a, zeroOk) && bsOf(a).length > 0 : bRange(a)) A.push(a);
  }
  return { A, pickB };
}
