// Draws one Halbschriftlich block.

import { sane as saneHalb, made as halbMade, layout as halbLayout, opLabel as halbOp } from "../../halbschriftlich";
import type { HalbschriftlichBlock } from "../tasks";

// A Halbschriftlich: its tasks side by side, in squares of Q units. A task has a line for the task (a + b = r), one line
// per step and a note row. Each number is D squares wide; the given numbers show on the sheet, the others in the key.
export const HEAD_LETTERS = ["T", "H", "Z", "E"];
export function Halbschriftlich({ block, solved }: { block: HalbschriftlichBlock; solved: boolean }) {
  const p = saneHalb(block.props);
  const { tasks, S, D } = halbMade(p);
  const { Q, CG, RG, TW, TH, across, vbW, vbH, headRows } = halbLayout(p);
  // The columns of a line: a, the sign, b, the =, r; a number starts at these squares.
  const at = [0, D + 1, 2 * D + 2];
  let karo = "";
  for (let x = 0; x < vbW; x += Q) karo += `M${x} 0V${vbH}`;
  for (let y = 0; y < vbH; y += Q) karo += `M0 ${y}H${vbW}`;
  return (
    <div className={`halbschriftlich${solved ? " solved" : ""}`}>
      <svg viewBox={`0 0 ${vbW} ${vbH}`} preserveAspectRatio="xMidYMin meet">
        <g transform="translate(0.5 0.5)">
          {p.grid && (
            <g className="karo" fill="none" stroke="#9fb4c8" strokeWidth={0.15}>
              <path d={karo} />
            </g>
          )}
          {tasks.map((t, i) => {
            const x0 = (i % across) * (TW + CG);
            const y0 = Math.floor(i / across) * (TH + RG);
            const blank = t.none;
            // The key shows the answers of a task that is not wrong and not empty; a wrong or empty task's key is its sheet.
            const open = solved && !t.wrong && !blank;
            const stepSigns = !blank && (p.ops || open);
            // A task with many answers gets S lines, room for any of them.
            const steps = t.wrong || blank || t.many ? S : t.steps.length;
            const kind = (pos: number): "given" | "answer" | null => (t.given[pos] ? "given" : open ? "answer" : null);
            // One slot: its digits as one text, right-aligned in its D squares, and in the plain layout its white box.
            const slot = (l: number, pos: number, value: number | null, k: "given" | "answer" | null) => {
              const x = x0 + at[pos] * Q;
              const y = y0 + (headRows + l) * Q;
              const digits = value === null ? "" : String(value);
              const xs = [...digits].map((_, j) => x + (D - digits.length + j + 0.5) * Q).join(" ");
              return (
                <g key={pos} className="slot" data-line={l} data-pos={pos}>
                  {!p.grid && <rect x={x} y={y} width={D * Q} height={Q} fill="white" stroke="#222" strokeWidth={0.3} />}
                  {p.tint && pos === 1 && <rect className="tint" x={x} y={y} width={D * Q} height={Q} fill="#9cc3f5" fillOpacity={0.35} />}
                  {k && (
                    <text className={k} x={xs} y={y + Q / 2} fontSize={Q * 0.75} fill={k === "given" ? "#222" : "#c0392b"} textAnchor="middle" dominantBaseline="central">
                      {digits}
                    </text>
                  )}
                </g>
              );
            };
            const signs = (l: number) => {
              const y = y0 + (headRows + l) * Q + Q / 2;
              return (
                <>
                  <text className="op" x={x0 + (D + 0.5) * Q} y={y} fontSize={Q * 0.75} fill="#222" textAnchor="middle" dominantBaseline="central">{halbOp(t.op)}</text>
                  <text className="eq" x={x0 + (2 * D + 1.5) * Q} y={y} fontSize={Q * 0.75} fill="#222" textAnchor="middle" dominantBaseline="central">=</text>
                </>
              );
            };
            return (
              <g key={i} className={`task${t.wrong ? " wrong" : ""}${t.many ? " many" : ""}${blank ? " none" : ""}`} data-task={i}>
                <g>
                  {[0, 1, 2].map((pos) => slot(0, pos, kind(pos) ? t.values[pos] : null, kind(pos)))}
                  {!blank && signs(0)}
                </g>
                {Array.from({ length: steps }, (_, j) => {
                  const st = open ? t.steps[j] : undefined;
                  return (
                    <g key={j}>
                      {slot(j + 1, 0, st ? st[0] : null, st ? "answer" : null)}
                      {slot(j + 1, 1, st ? st[1] : null, st ? "answer" : null)}
                      {slot(j + 1, 2, st ? st[2] : null, st ? "answer" : null)}
                      {stepSigns && signs(j + 1)}
                    </g>
                  );
                })}
                {p.head && !blank &&
                  at.flatMap((c) =>
                    HEAD_LETTERS.map((letter, k) => (
                      <text key={`${c}-${k}`} className="head" x={x0 + (c + k + 0.5) * Q} y={y0 + Q / 2} fontSize={Q * 0.6} fill="#555" textAnchor="middle" dominantBaseline="central">
                        {letter}
                      </text>
                    )),
                  )}
                {solved && t.many && !t.wrong && (
                  <text className="note" x={x0 + TW / 2} y={y0 + TH - Q / 2} fontSize={Q * 0.6} fill="#c0392b" textAnchor="middle" dominantBaseline="central">
                    Auch andere Lösungen sind richtig.
                  </text>
                )}
              </g>
            );
          })}
        </g>
      </svg>
    </div>
  );
}
