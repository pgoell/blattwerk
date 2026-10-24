// Draws the maths exercises of one block.

import { decimal, decimalsOf, GAP } from "../decimal";
import { KARO, PT } from "../height";
import { useLetters } from "./context";
import { type Calc, type Side, SIGNS, type Grid, type MathsBlock, type Exercise } from "./maths";
import { Count } from "./numbering";
import { useRef, useLayoutEffect, type CSSProperties } from "react";

// A number of an exercise, or the gap in its place. The answer key fills the gap.
// With Geld a number has its euro after it, outside the gap. The rest of a division is never a decimal.
export function Part({ e, part, solved, d, money }: { e: Calc; part: "a" | "b" | "c" | "result" | "rest"; solved: boolean; d: number; money: boolean }) {
  const gap = part === "rest" || part === (e.hide ?? "result");
  const text = part === "rest" ? decimal(e.rest, 0) : decimal(e[part] as number, d, money);
  const euro = money && part !== "rest" ? " €" : "";
  return <>{gap ? <u>{solved && text}</u> : text}{euro}</>;
}

// One side of a comparison as it reads: a number, or a term with its sign.
export const side = (s: Side) => (s.op ? `${decimal(s.a as number, 0)} ${SIGNS[s.op] ?? s.op} ${decimal(s.b as number, 0)}` : decimal(s.value, 0));

// A written exercise: squared paper with a character to a square. All of a block's exercises get the same paper.
// A square is `S` units wide: with a square of one unit a digit is under a unit high, and Chromium sets so small a
// type a whole square too high, on the screen and in every PDF (issue #446).
export function Karo({ grid, cols, rows, k, solved, dx, sign }: { grid: Grid; cols: number; rows: number; k: number; solved: boolean; dx: number; sign: boolean }) {
  const S = 10;
  const each = (n: number) => Array.from({ length: n + 1 }, (_, i) => i * S);
  // The task's own grid is narrower than the paper: it moves right, so its ones stand in the paper's last column.
  // A rule from the sign column stays there, so the rule under the sum spans the whole paper, and so does the sign
  // of a plus or a minus: every task of the block has it in the first column.
  const at = (x: number) => (sign && x === 0 ? 0 : x + dx);
  return (
    <svg width={cols * KARO * k} height={rows * KARO * k} viewBox={`0 0 ${cols * S} ${rows * S}`} style={{ width: `calc(${cols * KARO * k}px * var(--fit, 1))`, height: `calc(${rows * KARO * k}px * var(--fit, 1))` }}>
      <g stroke="#9db4c8" strokeWidth={0.03 * S}>
        {each(cols).map((x) => <line key={x} x1={x} x2={x} y2={rows * S} />)}
        {each(rows).map((y) => <line key={-y - 1} x2={cols * S} y1={y} y2={y} />)}
      </g>
      {grid.lines.map(([x1, x2, y, kind], i) => (solved || !kind) && <line key={i} className={kind ? "answer" : ""} x1={(x1 === 0 ? 0 : x1 + dx) * S} x2={(x2 + dx) * S} y1={y * S} y2={y * S} stroke="currentColor" strokeWidth={0.08 * S} />)}
      {grid.cells.map(([x, y, ch, kind], i) => (solved || !kind) && (
        <text key={i} className={kind ? "answer" : ""} x={(at(x) + 0.5) * S} y={(y + 0.5) * S} fontSize={(kind === 2 ? 0.45 : 0.75) * S} textAnchor="middle" dominantBaseline="central" fill="currentColor">
          {ch}
        </text>
      ))}
    </svg>
  );
}

// The scale each maths block draws at, by block id: below 1 when its tasks are too wide for it. The panel shows it as a hint.
// It is measured on the screen and kept nowhere in the document.
export const scales = new Map<string, number>();
export const scaleListeners = new Set<() => void>();
export function subscribe(listen: () => void) {
  scaleListeners.add(listen);
  return () => void scaleListeners.delete(listen);
}
export const scaleOf = (id: string) => scales.get(id) ?? 1;

export function Maths({ block, k, solved }: { block: MathsBlock; k: number; solved: boolean }) {
  const p = block.props;
  const letters = useLetters(block.id);
  const cols = Math.max(0, ...p.exercises.map((e) => ("sign" in e ? 0 : e.grid?.cols ?? 0)));
  const rows = Math.max(0, ...p.exercises.map((e) => ("sign" in e ? 0 : e.grid?.rows ?? 0)));
  const d = decimalsOf(p);
  const money = d > 0 && !!p.money;
  const root = useRef<HTMLDivElement>(null);
  // A gap holds the longest number, with its comma and its places after it. Each group gap of its thousands takes a bit more.
  const groupGaps = decimal(p.max, 0).split(GAP).length - 1;
  const style = { fontSize: `calc(${p.size * PT * k}px * var(--fit, 1))`, gridTemplateColumns: `repeat(${p.columns}, 1fr)`, "--gap": `${String(p.max).length + 1.5 + (d ? d + 1 : 0) + 0.3 * groupGaps}ch` };
  const num = { solved, d, money };
  // Tasks wider than the block shrink the type, as PowerPoint shrinks a text. Everything inside is in em, so the
  // width is linear in the scale and one measurement is enough.
  function fit() {
    const el = root.current;
    if (!el) return;
    el.style.removeProperty("--fit");
    // The numbers take the width of the widest one, in em so it scales with the type. offsetWidth is the laid out
    // width, whole pixels and blind to a turn of the block; one pixel more holds the fraction it drops.
    el.style.removeProperty("--num");
    const marks = [...el.querySelectorAll<HTMLElement>("b")];
    if (marks.length) el.style.setProperty("--num", `${(Math.max(...marks.map((b) => b.offsetWidth)) + 1) / parseFloat(getComputedStyle(el).fontSize)}em`);
    // A block with no width to speak of has no scale: it would come out below nothing.
    const over = el.clientWidth > 2 && el.scrollWidth > el.clientWidth + 1;
    // Two pixels of room: the paper's outer line lies half outside its svg, and the block cuts what leaves it.
    const scale = over ? (el.clientWidth - 2) / el.scrollWidth : 1;
    if (over) el.style.setProperty("--fit", String(scale));
    if (scales.get(block.id) !== scale) {
      scales.set(block.id, scale);
      scaleListeners.forEach((listen) => listen());
    }
  }
  useLayoutEffect(() => {
    fit();
  });
  // The fonts load after the first layout, and a wider letter makes a wider task. A cut loads when it is first
  // needed: the bold one with the numbering.
  useLayoutEffect(() => {
    document.fonts.ready.then(fit);
    document.fonts.addEventListener("loadingdone", fit);
    return () => document.fonts.removeEventListener("loadingdone", fit);
  }, []);
  // The numbering runs through every task. With families, the tasks of one family stand together in one grid item.
  const task = (e: Exercise, i: number) => (
    <div key={i}>
      {p.numbering && <b><Count mark={p.numbering} n={i + 1} /></b>}
      {"sign" in e ? (
        // The ring is empty for the pupil to write the sign in; the answer key writes it there.
        <span>
          {side(e.left)} <i className="ring">{solved && e.sign}</i> {side(e.right)}
        </span>
      ) : e.grid ? (
        // A division keeps its head on the left, as written.
        <Karo grid={e.grid} cols={cols} rows={rows} k={k} solved={solved} dx={e.op === "/" ? 0 : cols - e.grid.cols} sign={e.op === "+" || e.op === "-"} />
      ) : e.op2 ? (
        // The brackets stand against their numbers, as written: `(2 + 3) · 4` or `2 · (3 + 4)`.
        <span>
          {e.paren === "left" && "("}<Part e={e} part="a" {...num} /> {SIGNS[e.op] ?? e.op} {e.paren === "right" && "("}<Part e={e} part="b" {...num} />{e.paren === "left" && ")"} {SIGNS[e.op2] ?? e.op2} <Part e={e} part="c" {...num} />{e.paren === "right" && ")"} = <Part e={e} part="result" {...num} />
        </span>
      ) : (
        <span>
          <Part e={e} part="a" {...num} /> {SIGNS[e.op] ?? e.op} <Part e={e} part="b" {...num} /> = <Part e={e} part="result" {...num} />
          {e.rest > 0 && <> R <Part e={e} part="rest" {...num} /></>}
        </span>
      )}
      {letters && <span className="letter" data-task={i}>{solved ? letters[i] ?? "" : ""}</span>}
    </div>
  );
  // Consecutive exercises of one family share a group; a task with no family is a group of its own.
  const groups: number[][] = [];
  let prev: number | undefined;
  p.exercises.forEach((e, i) => {
    const family = "sign" in e ? undefined : e.family;
    if (family !== undefined && family === prev) groups[groups.length - 1].push(i);
    else groups.push([i]);
    prev = family;
  });
  const families = p.exercises.some((e) => !("sign" in e) && e.family !== undefined);
  return (
    // The format's class has a name of its own: `gap` and `written` are a text's gap and a Lineatur's text.
    <div ref={root} className={`maths maths-${p.format}${solved ? " solved" : ""}`} style={style as CSSProperties}>
      {groups.map((g) => (families ? <div key={g[0]} className="family">{g.map((i) => task(p.exercises[i], i))}</div> : task(p.exercises[g[0]], g[0])))}
      {!p.exercises.length && <span className="hint">Keine Aufgabe möglich</span>}
    </div>
  );
}
