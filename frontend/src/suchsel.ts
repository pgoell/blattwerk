// The Suchsel (word search): where each word lies in the grid and what letters stand around it. A pure function of
// the block's settings and its seed, so the editor, the thumbnail and the PDF draw the same grid.
import { wordsIn, type SuchselProps } from "./sheet";

// A hidden word: `word` as the teacher typed it, `letters` as the grid shows it, a square to an entry, from the square
// at column `col` and row `row` (both from 0) on by `dc` columns and `dr` rows a letter.
export type Hidden = { word: string; letters: string[]; col: number; row: number; dc: number; dr: number };
// What can make room for a word that does not fit: more columns or rows, more directions, fewer words.
export type Loosen = "size" | "ways" | "words";
// The grid, a row of columns at a time, and the hidden words in the order typed. `missed` holds the words that found
// no room, as typed, with what to loosen for them in `loosen`; `short` the words of fewer than 3 letters, which are
// never hidden.
export type Laid = { grid: string[][]; hidden: Hidden[]; missed: string[]; short: string[]; loosen: Loosen[] };

// The eight directions a run may take, for the check that no word is spelt a second time.
const EIGHT: [number, number][] = [[1, 0], [-1, 0], [0, 1], [0, -1], [1, 1], [1, -1], [-1, 1], [-1, -1]];

// German letters with their weights in percent, for the fill. The umlauts and ß come in only with `umlauts`.
const WEIGHTS: [string, number][] = [["E", 17.4], ["N", 9.78], ["I", 7.55], ["S", 7.27], ["R", 7], ["A", 6.51], ["T", 6.15], ["D", 5.08], ["H", 4.76], ["U", 4.35], ["L", 3.44], ["C", 3.06], ["G", 3.01], ["M", 2.53], ["O", 2.51], ["B", 1.89], ["W", 1.89], ["F", 1.66], ["K", 1.21], ["Z", 1.13], ["P", 0.79], ["V", 0.67], ["J", 0.27], ["Y", 0.04], ["X", 0.03], ["Q", 0.02]];
const UMLAUTS: [string, number][] = [["Ü", 0.65], ["Ä", 0.54], ["Ö", 0.3], ["ß", 0.31]];

// The spelling of umlauts and ß when they are not kept.
const SPELT: Record<string, string> = { ä: "ae", ö: "oe", ü: "ue", ß: "ss", Ä: "Ae", Ö: "Oe", Ü: "Ue" };

// The layouts made so far, by their settings, so the editor does not lay a grid out on every render. The oldest goes
// once there are more than 50.
const made = new Map<string, Laid>();

// The settings as a grid can take them, whatever a stored sheet holds: 6 to 20 columns and rows, a known `ways`.
export function sane(p: SuchselProps): SuchselProps {
  const size = (n: number) => (Number.isFinite(n) ? Math.min(20, Math.max(6, Math.round(n))) : 10);
  return {
    words: Array.isArray(p.words) ? p.words : [],
    cols: size(p.cols),
    rows: size(p.rows),
    ways: p.ways === "down" || p.ways === "diag" || p.ways === "back" ? p.ways : "across",
    caps: p.caps !== false,
    umlauts: p.umlauts !== false,
    show: p.show === "count" ? "count" : "words",
    seed: Number.isFinite(p.seed) ? p.seed : 0,
  };
}

// A word as the grid shows it, a square to an entry: letters only, capitals or small, ä, ö, ü and ß kept or spelt out.
export function letters(word: string, caps: boolean, umlauts: boolean): string[] {
  const text = word.normalize("NFC").replace(/ẞ/g, "ß");
  const kept = umlauts ? text : text.replace(/[äöüßÄÖÜ]/g, (c) => SPELT[c]);
  return [...kept].filter((c) => /\p{L}/u.test(c)).map((c) => (caps ? (c === "ß" ? c : c.toLocaleUpperCase("de")) : c.toLocaleLowerCase("de")));
}

// The layout of a block. The same settings give the same layout on every call.
export function laid(props: SuchselProps): Laid {
  const p = sane(props);
  const key = JSON.stringify(p);
  const old = made.get(key);
  if (old) return old;
  const out = lay(p);
  made.set(key, out);
  if (made.size > 50) made.delete(made.keys().next().value as string);
  return out;
}

// A seeded generator of numbers from 0 up to 1: mulberry32, as `shuffled` in bank.ts.
function rng(seed: number) {
  let a = seed | 0;
  return () => {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = ((t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t) | 0;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// The squares of a run of `n` letters from (col, row) on by (dc, dr), or undefined when the run leaves the grid.
function run(cols: number, rows: number, col: number, row: number, dc: number, dr: number, n: number): [number, number][] | undefined {
  const squares: [number, number][] = [];
  for (let k = 0; k < n; k++) {
    const c = col + k * dc;
    const r = row + k * dr;
    if (c < 0 || r < 0 || c >= cols || r >= rows) return undefined;
    squares.push([c, r]);
  }
  return squares;
}

// Lays out settings that are already sane: places the words, fills the rest and takes out any second spelling.
function lay(p: SuchselProps): Laid {
  const { cols, rows } = p;
  const next = rng(p.seed);

  // Each typed word once, as its letters. A word of fewer than 3 letters is short and never hidden.
  const seen = new Set<string>();
  const short: string[] = [];
  const typed: { word: string; letters: string[] }[] = [];
  for (const word of wordsIn({ words: p.words })) {
    const ls = letters(word, p.caps, p.umlauts);
    if (seen.has(ls.join(""))) continue;
    seen.add(ls.join(""));
    if (ls.length < 3) short.push(word);
    else typed.push({ word, letters: ls });
  }

  const dirs: [number, number][] = [[1, 0]];
  if (p.ways !== "across") dirs.push([0, 1]);
  if (p.ways === "diag" || p.ways === "back") dirs.push([1, 1], [1, -1]);
  if (p.ways === "back") dirs.push([-1, 0], [0, -1], [-1, -1], [-1, 1]);

  // The longest word first, each at a place it fits picked by the generator. A word that fits nowhere stays unplaced.
  const grid = Array.from({ length: rows }, () => Array<string>(cols).fill(""));
  const fill = Array.from({ length: rows }, () => Array<boolean>(cols).fill(false));
  const slot: (Hidden | undefined)[] = [];
  const order = typed.map((_, i) => i).sort((a, b) => typed[b].letters.length - typed[a].letters.length);
  for (const i of order) {
    const { word, letters: ls } = typed[i];
    const fits: Hidden[] = [];
    for (const [dc, dr] of dirs) {
      for (let row = 0; row < rows; row++) {
        for (let col = 0; col < cols; col++) {
          const sq = run(cols, rows, col, row, dc, dr, ls.length);
          if (sq?.every(([c, r], k) => grid[r][c] === "" || grid[r][c] === ls[k])) fits.push({ word, letters: ls, col, row, dc, dr });
        }
      }
    }
    if (!fits.length) continue;
    const h = fits[Math.floor(next() * fits.length)];
    for (let k = 0; k < ls.length; k++) grid[h.row + k * h.dr][h.col + k * h.dc] = ls[k];
    slot[i] = h;
  }
  const hidden = slot.filter((h): h is Hidden => h !== undefined);
  const missed = typed.flatMap((t, i) => (slot[i] ? [] : [t.word]));

  // What would make room for the missed words. The fixed order is size, ways, words.
  const small = cols < 20 || rows < 20;
  const need = new Set<Loosen>();
  for (let i = 0; i < typed.length; i++) {
    if (slot[i]) continue;
    const n = typed[i].letters.length;
    if (n > (p.ways === "across" ? cols : Math.max(cols, rows))) {
      if (small) need.add("size");
      if (p.ways === "across" && n <= rows) need.add("ways");
    } else {
      if (small) need.add("size");
      if (p.ways !== "back") need.add("ways");
      need.add("words");
    }
  }
  const loosen = (["size", "ways", "words"] as Loosen[]).filter((l) => need.has(l));

  // Every empty square takes a letter by weight, cased as the settings say.
  const cased = (c: string) => (p.caps || c === "ß" ? c : c.toLocaleLowerCase("de"));
  const pool = p.umlauts ? [...WEIGHTS, ...UMLAUTS] : WEIGHTS;
  const total = pool.reduce((sum, [, w]) => sum + w, 0);
  const draw = () => {
    let r = next() * total;
    for (const [c, w] of pool) {
      r -= w;
      if (r < 0) return cased(c);
    }
    return cased(pool[pool.length - 1][0]);
  };
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      if (grid[r][c] !== "") continue;
      grid[r][c] = draw();
      fill[r][c] = true;
    }
  }

  // The runs that spell a typed word in any of the eight directions and use a fill square, each as its squares and its
  // word. With `at`, only the runs through that square.
  const forms = typed.map((t) => t.letters);
  const bad = (at?: [number, number]) => {
    const found: { sq: [number, number][]; ls: string[] }[] = [];
    for (const ls of forms) {
      for (const [dc, dr] of EIGHT) {
        for (let r = 0; r < rows; r++) {
          for (let c = 0; c < cols; c++) {
            const sq = run(cols, rows, c, r, dc, dr, ls.length);
            if (!sq || !sq.every(([x, y], k) => grid[y][x] === ls[k])) continue;
            if (!sq.some(([x, y]) => fill[y][x])) continue;
            if (at && !sq.some(([x, y]) => x === at[0] && y === at[1])) continue;
            found.push({ sq, ls });
          }
        }
      }
    }
    return found;
  };

  // Each sweep takes the runs that spell a word through a fill square, and changes a fill square of each one that still
  // spells its word. The first 30 sweeps give the square a random letter; the next 30 give it the first letter in the
  // weights' order under which no run through it spells a word. After 60 sweeps it stops, whatever stands, so that no
  // list can hang the page.
  for (let n = 0; n < 60; n++) {
    const runs = bad();
    if (!runs.length) break;
    for (const { sq, ls } of runs) {
      if (!sq.every(([x, y], k) => grid[y][x] === ls[k])) continue;
      const [x, y] = sq.find(([u, v]) => fill[v][u]) as [number, number];
      if (n < 30) {
        let l = draw();
        while (l === grid[y][x]) l = draw();
        grid[y][x] = l;
      } else {
        for (const [c] of pool) {
          grid[y][x] = cased(c);
          if (!bad([x, y]).length) break;
        }
      }
    }
  }

  return { grid, hidden, missed, short, loosen };
}
