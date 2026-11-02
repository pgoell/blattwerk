// The inner numbers nearest to a generated triple whose products hold the numbers the teacher typed.
// Field 0 to 2 are the inner numbers, 3 to 5 the products of the sides [0, 1], [1, 2] and [2, 0].

const SIDES: [number, number][] = [
  [0, 1],
  [1, 2],
  [2, 0],
];

const product = (t: number[], f: number): number => (f < 3 ? t[f] : t[SIDES[f - 3][0]] * t[SIDES[f - 3][1]]);

function holds(t: number[], typed: Map<number, number>): boolean {
  if (t.some((v) => !Number.isInteger(v) || v < 0 || v > 9999)) return false;
  if (SIDES.some(([a, b]) => t[a] * t[b] > 9999)) return false;
  for (const [f, v] of typed) if (product(t, f) !== v) return false;
  return true;
}

function divisors(n: number): number[] {
  const out: number[] = [];
  for (let d = 1; d * d <= n; d++) if (n % d === 0) {
    out.push(d);
    if (d * d !== n && n / d <= 9999) out.push(n / d);
  }
  return out;
}

const nearer = (a: number[], b: number[], gen: number[]): boolean => {
  const da = a.reduce((s, v, i) => s + Math.abs(v - gen[i]), 0);
  const db = b.reduce((s, v, i) => s + Math.abs(v - gen[i]), 0);
  if (da !== db) return da < db;
  for (let i = 0; i < a.length; i++) if (a[i] !== b[i]) return a[i] < b[i];
  return false;
};

// Values inner `i` may take, given the inners already chosen in `cur` (indexes below `i`).
function domain(i: number, typed: Map<number, number>, gen: number[], cur: number[]): number[] {
  if (typed.has(i)) {
    const v = typed.get(i) as number;
    return Number.isInteger(v) && v >= 0 && v <= 9999 ? [v] : [];
  }
  const quotients: number[][] = [];
  const openDivs: number[][] = [];
  let openZero = false;
  for (let s = 0; s < 3; s++) {
    if (!typed.has(3 + s)) continue;
    const [a, b] = SIDES[s];
    if (a !== i && b !== i) continue;
    const j = a === i ? b : a;
    const v = typed.get(3 + s) as number;
    if (typed.has(j) || j < i) {
      const other = typed.has(j) ? (typed.get(j) as number) : cur[j];
      if (other === 0) {
        if (v !== 0) return [];
      } else if (v % other === 0 && v / other <= 9999) quotients.push([v / other]);
      else return [];
    } else if (v > 0) openDivs.push(divisors(v));
    else openZero = true;
  }
  let set: number[] | null = null;
  for (const list of [...quotients, ...openDivs]) set = set === null ? list : set.filter((v) => list.includes(v));
  if (set === null) return openZero ? [0, gen[i]] : [gen[i]];
  return set;
}

// Undefined when no whole triple from 0 to 9999 holds the typed products.
export function fillTimes(typed: Map<number, number>, gen: number[]): number[] | undefined {
  let best: number[] | undefined;
  const cur = [0, 0, 0];
  const walk = (i: number): void => {
    if (i === 3) {
      if (holds(cur, typed) && (!best || nearer(cur, best, gen))) best = [...cur];
      return;
    }
    for (const v of domain(i, typed, gen, cur)) {
      cur[i] = v;
      walk(i + 1);
    }
  };
  walk(0);
  return best;
}
