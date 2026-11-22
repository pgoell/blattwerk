// Draws the maths exercises of one block.

import { decimal, decimalsOf, GAP } from "../decimal";
import { asFormula } from "../formula";
import { FormulaCell, FormulaText } from "./formulaView";
import { HtmlInk, SvgInk, usePlaces } from "./places";
import { gridTint } from "../places";
import { KARO, PT } from "../height";
import { useLetters } from "./context";
import { type Calc, type Side, SIGNS, type Grid, type MathsBlock, type Exercise } from "./maths";
import { Count } from "./numbering";
import { useRef, useLayoutEffect, type CSSProperties, type ReactNode } from "react";

// The pieces of a task that stand under the same piece of the tasks above and below: the numbers, the signs between
// them, the brackets of a chain and the left side of a comparison.
const ATS = ["a", "b", "c", "result", "op", "op2", "close-b", "close-c", "left"] as const;
type AtName = (typeof ATS)[number];

// One such piece. `fit` gives every piece of a kind the width of the block's widest, so the ones stand under the
// ones, the signs under the signs and the answer lines under each other (#1160).
function At({ at, children }: { at: AtName; children?: ReactNode }) {
  return <span className="at" data-at={at} style={{ minWidth: `var(--at-${at}, 0)` }}>{children}</span>;
}

// A number of an exercise, or the gap in its place. The answer key fills the gap.
// With Geld a number has its euro after it, outside the gap. The rest of a division is never a decimal.
// A bracket that opens before the number stands against it, in the number's piece: the ones stay where they are.
function Part({ e, part, solved, d, money, blank = true, open = false }: { e: Calc; part: "a" | "b" | "c" | "result" | "rest"; solved: boolean; d: number; money: boolean; blank?: boolean; open?: boolean }) {
  const gap = part === "rest" ? blank : part === (e.hide ?? "result") || part === e.also;
  const text = part === "rest" ? decimal(e.rest, 0) : decimal(e[part] as number, d, money);
  const euro = money && part !== "rest" ? " €" : "";
  const shown = <FormulaText text={text} />;
  const number = gap ? <u>{solved && shown}</u> : shown;
  return <>{part === "rest" ? number : <At at={part}>{open && "("}{number}</At>}{euro}</>;
}

// One side of a comparison as it reads: a number, or a term with its sign.
export const side = (s: Side) => (s.op ? `${decimal(s.a as number, 0)} ${SIGNS[s.op] ?? s.op} ${decimal(s.b as number, 0)}` : decimal(s.value, 0));

// A written exercise: squared paper with a character to a square. All of a block's exercises get the same paper.
// A square is `S` units wide: with a square of one unit a digit is under a unit high, and Chromium sets so small a
// type a whole square too high, on the screen and in every PDF (issue #446).
export function Karo({ grid, cols, rows, k, solved, dx, sign }: { grid: Grid; cols: number; rows: number; k: number; solved: boolean; dx: number; sign: boolean }) {
  const S = 10;
  const tint = gridTint(grid.cells.map(([x, y, ch, kind]) => ({ x, y, ch, kind })), usePlaces());
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
      {grid.cells.map(([x, y, ch, kind], i) => {
        // Kind 3 is a place letter: it prints on the pupil's sheet, smaller, and in grey.
        if (!solved && kind && kind !== 3) return null;
        const formula = asFormula(ch);
        const head = kind === 3;
        const em = (kind === 2 ? 0.45 : head ? (ch.length > 1 ? 0.42 : 0.55) : 0.75) * S;
        const hit = !head && ch.length === 1 ? tint.get(`${x},${y}`) : undefined;
        return formula ? (
          <FormulaCell key={i} source={formula} x={at(x) * S} y={y * S} side={S} em={em} />
        ) : (
          <text key={i} className={head ? "head" : kind ? "answer" : ""} data-place={hit?.place} x={(at(x) + 0.5) * S} y={(y + 0.5) * S} fontSize={em} textAnchor="middle" dominantBaseline="central" fill={head ? "#555" : "currentColor"} style={hit ? { fill: hit.color } : undefined}>
            {!head && ch.length > 1 ? <SvgInk text={ch} /> : ch}
          </text>
        );
      })}
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
  // A sheet from before the choice keeps the remainder as a gap. A chosen Lücke follows the ticks.
  const restBlank = p.format !== "gap" || (p.gaps ? p.gaps.includes("rest") : true);
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
    const em = parseFloat(getComputedStyle(el).fontSize);
    if (marks.length) el.style.setProperty("--num", `${(Math.max(...marks.map((b) => b.offsetWidth)) + 1) / em}em`);
    // So do the pieces of the tasks, kind by kind. A kind whose pieces are all one width already keeps it.
    for (const at of ATS) el.style.removeProperty(`--at-${at}`);
    const widths = new Map<string, number[]>();
    for (const piece of el.querySelectorAll<HTMLElement>(".at")) widths.set(piece.dataset.at!, [...(widths.get(piece.dataset.at!) ?? []), piece.offsetWidth]);
    for (const [at, ws] of widths) if (Math.max(...ws) > Math.min(...ws)) el.style.setProperty(`--at-${at}`, `${(Math.max(...ws) + 1) / em}em`);
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
  // A closing bracket has a place of its own after its number, where any task of the block has one there.
  const paren = (where: "left" | "right") => p.exercises.some((e) => !("sign" in e) && e.paren === where);
  const [left, right] = [paren("left"), paren("right")];
  const sign = (op: string) => SIGNS[op as keyof typeof SIGNS] ?? op;
  // The numbering runs through every task. With families, the tasks of one family stand together in one grid item.
  const task = (e: Exercise, i: number) => (
    <div key={i}>
      {p.numbering && <b><Count mark={p.numbering} n={i + 1} /></b>}
      {"sign" in e ? (
        // The ring is empty for the pupil to write the sign in; the answer key writes it there.
        <span>
          <At at="left"><HtmlInk text={side(e.left)} /></At> <i className="ring">{solved && e.sign}</i> <HtmlInk text={side(e.right)} />
        </span>
      ) : e.grid ? (
        // A division keeps its head on the left, as written.
        <Karo grid={e.grid} cols={cols} rows={rows} k={k} solved={solved} dx={e.op === "/" ? 0 : cols - e.grid.cols} sign={e.op === "+" || e.op === "-"} />
      ) : e.op2 ? (
        // The brackets stand against their numbers, as written: `(2 + 3) · 4` or `2 · (3 + 4)`.
        <span>
          <Part e={e} part="a" {...num} open={e.paren === "left"} /> <At at="op">{sign(e.op)}</At> <Part e={e} part="b" {...num} open={e.paren === "right"} />{left && <At at="close-b">{e.paren === "left" && ")"}</At>} <At at="op2">{sign(e.op2)}</At> <Part e={e} part="c" {...num} />{right && <At at="close-c">{e.paren === "right" && ")"}</At>} = <Part e={e} part="result" {...num} />
        </span>
      ) : (
        <span>
          <Part e={e} part="a" {...num} /> <At at="op">{sign(e.op)}</At> <Part e={e} part="b" {...num} /> = <Part e={e} part="result" {...num} />
          {e.rest > 0 && <> R <Part e={e} part="rest" {...num} blank={restBlank} /></>}
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
