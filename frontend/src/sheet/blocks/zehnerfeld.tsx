// Draws one Zehnerfeld block.

import { sane as saneZehn, made as zehnMade, acts as zehnActs, colorsOf as zehnColors, layout as zehnLayout, opLabel as zehnOp } from "../../zehnerfeld";
import type { ZehnerfeldBlock } from "../tasks";

// A Zehnerfeld: its tasks side by side, each a field of dots with its task line under it (a box, the sign, a box, the
// =, a box). The dots and numbers the task shows on the sheet; the key adds the answers. Its layout is the contract's.
export function Zehnerfeld({ block, solved }: { block: ZehnerfeldBlock; solved: boolean }) {
  const p = saneZehn(block.props);
  const { tasks } = zehnMade(p);
  const { C, rows, cols } = zehnActs(p);
  const [color1, color2] = zehnColors(p);
  const { U, B, LH, G, FW, FH, LW, TW, TH, CG, RG, across, vbW, vbH } = zehnLayout(p);
  const marks = p.marks ?? [];
  // The squares inside the frame, and the Trennlinien: after each five of a row of ten, of a column of ten, between the rows of five.
  let squares = "";
  for (let x = 0; x <= cols; x++) squares += `M${x * U} 0V${FH}`;
  for (let y = 0; y <= rows; y++) squares += `M0 ${y * U}H${FW}`;
  const trenn: [number, number, number, number][] = [];
  if (p.lines && cols === 10) trenn.push([5 * U, 0, 5 * U, FH]);
  if (p.lines && rows === 10) trenn.push([0, 5 * U, FW, 5 * U]);
  if (p.lines && cols === 5) for (let y = 1; y < rows; y++) trenn.push([0, y * U, FW, y * U]);
  // The dots of a task: the teacher's marks with `manual`; none for a wrong or empty task; the task's own dots in the key
  // and on a "dots" sheet, none on a "write" sheet.
  const dotsOf = (i: number, t: (typeof tasks)[number]): number[] => {
    if (p.manual) return Array.from({ length: C }, (_, j) => marks.find((e) => e[0] === i && e[1] === j)?.[2] ?? 0);
    if (t.wrong || t.none) return Array.from({ length: C }, () => 0);
    if (t.kind === "dots" || solved) return t.dots;
    return Array.from({ length: C }, () => 0);
  };
  // A box's number: the given ones on the sheet, the answers in the key; none for a manual, wrong or empty task.
  const numberOf = (t: (typeof tasks)[number], pos: number): { value: number; kind: "given" | "answer" } | null => {
    if (p.manual || t.wrong || t.none) return null;
    if (t.kind === "write" && pos < 2) return { value: t.values[pos], kind: "given" };
    return solved ? { value: t.values[pos], kind: "answer" } : null;
  };
  return (
    <div className={`zehnerfeld${solved ? " solved" : ""}`}>
      <svg viewBox={`0 0 ${vbW} ${vbH}`} preserveAspectRatio="xMidYMin meet">
        <g transform="translate(0.5 0.5)">
          {tasks.map((t, i) => {
            const x0 = (i % across) * (TW + CG);
            const y0 = Math.floor(i / across) * (TH + RG);
            const fx = x0 + (TW - FW) / 2;
            const bx = x0 + (TW - LW) / 2;
            const by = y0 + FH + G;
            const boxes = [bx, bx + B + 5, bx + 2 * B + 10];
            return (
              <g key={i} className={`task${t.wrong ? " wrong" : ""}${t.none ? " none" : ""}${p.manual ? " manual" : ""}`} data-task={i}>
                <g className="field" transform={`translate(${fx} ${y0})`}>
                  <rect x={0} y={0} width={FW} height={FH} fill="white" stroke="#222" strokeWidth={0.4} />
                  <path d={squares} fill="none" stroke="#bbb" strokeWidth={0.2} />
                  {trenn.map(([x1, y1, x2, y2], j) => (
                    <line key={j} className="trenn" x1={x1} y1={y1} x2={x2} y2={y2} stroke="#222" strokeWidth={0.8} />
                  ))}
                  {dotsOf(i, t).map((m, j) => {
                    const cx = ((j % cols) + 0.5) * U;
                    const cy = (Math.floor(j / cols) + 0.5) * U;
                    return (
                      <g key={j}>
                        <circle
                          className="dot"
                          data-k={j}
                          data-mark={m}
                          cx={cx}
                          cy={cy}
                          r={2.2}
                          fill={m === 0 ? "white" : m === 2 ? color2 : color1}
                          stroke={m === 0 ? "#888" : "none"}
                          strokeWidth={0.3}
                        />
                        {m === 3 &&
                          ["white", "#222"].map((stroke, s) => (
                            <line
                              key={s}
                              className="strike"
                              x1={cx - 2.2}
                              y1={cy + 2.2}
                              x2={cx + 2.2}
                              y2={cy - 2.2}
                              stroke={stroke}
                              strokeWidth={s === 0 ? 1.2 : 0.5}
                            />
                          ))}
                      </g>
                    );
                  })}
                </g>
                {boxes.map((x, pos) => {
                  const v = numberOf(t, pos);
                  return (
                    <g key={pos} className="slot" data-pos={pos}>
                      <rect x={x} y={by} width={B} height={LH} fill="white" stroke="#222" strokeWidth={0.3} />
                      {v && (
                        <text
                          className={v.kind}
                          x={x + B / 2}
                          y={by + LH / 2}
                          fontSize={5.5}
                          fill={v.kind === "given" ? "#222" : "#c0392b"}
                          textAnchor="middle"
                          dominantBaseline="central"
                        >
                          {v.value}
                        </text>
                      )}
                    </g>
                  );
                })}
                {(!t.none || p.manual) && (
                  <>
                    <text className="op" x={bx + B + 2.5} y={by + LH / 2} fontSize={5.5} fill="#222" textAnchor="middle" dominantBaseline="central">
                      {zehnOp(p.op)}
                    </text>
                    <text className="eq" x={bx + 2 * B + 7.5} y={by + LH / 2} fontSize={5.5} fill="#222" textAnchor="middle" dominantBaseline="central">
                      =
                    </text>
                  </>
                )}
              </g>
            );
          })}
        </g>
      </svg>
    </div>
  );
}
