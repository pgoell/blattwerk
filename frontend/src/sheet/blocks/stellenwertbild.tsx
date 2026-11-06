// Draws one Stellenwert-Bild block.

import { sane, made, layout, placesOf, formOf } from "../../stellenwertbild";
import { placeName } from "../../places";
import { SvgInk, usePlaces } from "../places";
import type { StellenwertbildBlock } from "../tasks";

// The size of a piece by its place's value: the plate (100), the rod (10) and the cube (1).
const SIZE: Record<number, [number, number]> = { 100: [12, 12], 10: [1.2, 12], 1: [1.2, 1.2] };
// The top left of slot k of a zone at x: plates 3 to a row, rods 10 to a row (a gap after five), cubes 5 to a row.
const slotOf = (v: number, k: number, x: number) =>
  v === 100
    ? { x: x + (k % 3) * 14, y: Math.floor(k / 3) * 14 }
    : v === 10
      ? { x: x + (k % 10) * 2.4 + (k % 10 >= 5 ? 1.2 : 0), y: Math.floor(k / 10) * 14 }
      : { x: x + (k % 5) * 2.4, y: Math.floor(k / 5) * 2.4 };

// A Stellenwert-Bild: its tasks side by side, each a picture of pieces (or, with "draw", an empty frame) with its line
// under it (the table, the form, the sign and the number box). The pieces and numbers the task shows on the sheet; the
// key adds the answers. Its layout is the contract's.
export function Stellenwertbild({ block, solved }: { block: StellenwertbildBlock; solved: boolean }) {
  const p = sane(block.props);
  const { tasks } = made(p);
  const { PW, PH, G, LW, LH, KL, FW, TW, TH, CG, RG, across, vbW, vbH, zones } = layout(p);
  const places = placesOf(p);
  const draw = p.task === "draw";
  // A table cell holds one digit, so it takes the colour of its column's place, not of a number read from its right.
  const colors = usePlaces();
  return (
    <div className={`stellenwertbild${solved ? " solved" : ""}`}>
      <svg viewBox={`0 0 ${vbW} ${vbH}`} preserveAspectRatio="xMidYMin meet">
        <g transform="translate(0.5 0.5)">
          {tasks.map((t, i) => {
            const x0 = (i % across) * (TW + CG);
            const y0 = Math.floor(i / across) * (TH + RG);
            const px = x0 + (TW - PW) / 2;
            const lx = x0 + (TW - LW) / 2;
            const ly = y0 + PH + G;
            // A wrong or empty task shows no piece, symbol, number or form; the key shows the answers of the rest.
            const shown = !t.wrong && !t.none;
            const answered = solved && shown;
            // The line: the table (read, with a table), the form (draw, with Bündeln) and the number box with its sign.
            const table = !draw && p.table;
            const boxH = table ? 8 : LH;
            const boxY = table ? ly + 5 : ly;
            const boxX = lx + (table ? places.length * 8 + 5 : draw && p.bundle ? FW + 5 : 0);
            const signX = table ? lx + places.length * 8 + 2.5 : lx + FW + 2.5;
            const hasSign = table || (draw && p.bundle);
            // "draw" shows its number on the sheet, every other box only in the key.
            const boxText = draw && !p.bundle ? (shown ? t.n : null) : answered ? t.n : null;
            return (
              <g key={i} className={`task${t.wrong ? " wrong" : ""}${t.none ? " none" : ""}`} data-task={i}>
                {draw ? (
                  <rect className="frame" x={px} y={y0} width={PW} height={PH} fill="white" stroke="#222" strokeWidth={0.3} />
                ) : (
                  shown &&
                  zones.map((z) => {
                    const [w, h] = SIZE[z.v];
                    const idx = places.findIndex((pl) => pl.v === z.v);
                    return Array.from({ length: t.counts[idx] }, (_, k) => {
                      const { x, y } = slotOf(z.v, k, px + z.x);
                      const inner: [number, number, number, number][] = [];
                      if (z.v === 100)
                        for (let m = 1; m <= 9; m++) inner.push([x + m * 1.2, y, x + m * 1.2, y + h], [x, y + m * 1.2, x + w, y + m * 1.2]);
                      if (z.v === 10) for (let m = 1; m <= 9; m++) inner.push([x, y + m * 1.2, x + w, y + m * 1.2]);
                      return (
                        <g key={`${z.v}-${k}`} className="piece" data-v={z.v}>
                          <rect x={x} y={y} width={w} height={h} fill="white" stroke="#222" strokeWidth={0.25} />
                          {inner.map(([x1, y1, x2, y2], j) => (
                            <line key={j} x1={x1} y1={y1} x2={x2} y2={y2} stroke="#999" strokeWidth={0.1} />
                          ))}
                        </g>
                      );
                    });
                  })
                )}
                {draw &&
                  answered &&
                  zones.map((z) => {
                    const idx = places.findIndex((pl) => pl.v === z.v);
                    return Array.from({ length: t.digits[idx] }, (_, k) => {
                      const { x, y } = slotOf(z.v, k, px + z.x);
                      if (z.v === 100)
                        return <rect key={`${z.v}-${k}`} className="sym" data-v={z.v} x={x + 3} y={y + 3} width={6} height={6} fill="none" stroke="#c0392b" strokeWidth={0.4} />;
                      if (z.v === 10)
                        return <line key={`${z.v}-${k}`} className="sym" data-v={z.v} x1={x + 0.6} y1={y} x2={x + 0.6} y2={y + 12} stroke="#c0392b" strokeWidth={0.4} />;
                      return <circle key={`${z.v}-${k}`} className="sym" data-v={z.v} cx={x + 0.6} cy={y + 0.6} r={0.6} fill="#c0392b" stroke="#c0392b" strokeWidth={0.4} />;
                    });
                  })}
                {table && (
                  <g className="table">
                    {places.map((pl, j) => {
                      const cx = lx + j * 8;
                      return (
                        <g key={pl.v}>
                          <text className="head" x={cx + 4} y={ly + 2.5} fontSize={4} fill="#222" textAnchor="middle" dominantBaseline="central">
                            {pl.letter}
                          </text>
                          <g className="cell" data-v={pl.v}>
                            <rect x={cx} y={ly + 5} width={8} height={8} fill="white" stroke="#222" strokeWidth={0.3} />
                            {answered && (
                              <text className="answer" x={cx + 4} y={ly + 9} fontSize={5.5} fill="#c0392b" textAnchor="middle" dominantBaseline="central">
                                {colors ? (
                                  <tspan data-place={placeName(places.length - 1 - j)} style={{ fill: colors[placeName(places.length - 1 - j)] }}>
                                    {t.digits[j]}
                                  </tspan>
                                ) : (
                                  t.digits[j]
                                )}
                              </text>
                            )}
                          </g>
                        </g>
                      );
                    })}
                  </g>
                )}
                {draw && p.bundle && shown && (
                  <text className="given form" x={lx + FW / 2} y={ly + LH / 2} fontSize={4.5} fill="#222" textAnchor="middle" dominantBaseline="central">
                    {formOf(p, t.counts)}
                  </text>
                )}
                {hasSign && (
                  <text className="eq" x={signX} y={boxY + boxH / 2} fontSize={5.5} fill="#222" textAnchor="middle" dominantBaseline="central">
                    =
                  </text>
                )}
                <g className="slot">
                  <rect x={boxX} y={boxY} width={16} height={boxH} fill="white" stroke="#222" strokeWidth={0.3} />
                  {boxText !== null && (
                    <text
                      className={draw && !p.bundle ? "given" : "answer"}
                      x={boxX + 8}
                      y={boxY + boxH / 2}
                      fontSize={5.5}
                      fill={draw && !p.bundle ? "#222" : "#c0392b"}
                      textAnchor="middle"
                      dominantBaseline="central"
                    >
                      <SvgInk text={boxText} />
                    </text>
                  )}
                </g>
                {!draw && p.bundle && answered && (
                  <text className="answer exchanged" x={x0 + TW / 2} y={ly + LH + KL / 2} fontSize={4} fill="#c0392b" textAnchor="middle" dominantBaseline="central">
                    {`= ${formOf(p, t.digits)}`}
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
