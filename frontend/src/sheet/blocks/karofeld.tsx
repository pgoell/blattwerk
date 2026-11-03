// Draws one Karofeld block.

import { fontOf, isoLines, sane } from "../../karofeld";
import { gridTint } from "../../places";
import type { KarofeldBlock } from "../tasks";
import type { Square } from "../../karofeld";
import { SvgInk, usePlaces } from "../places";

// A free grid: one digit or sign to a square. The viewBox is the field in mm, so a square of `size` mm
// keeps that size when the block is `boxOf`, and the letter is `fontOf(size)`.
export function Karofeld({ block, onSquare }: { block: KarofeldBlock; onSquare?: (col: number, row: number) => void }) {
  const p = sane(block.props);
  const places = usePlaces();
  const { cols, rows, size, look } = p;
  const [w, h] = [cols * size, rows * size];
  const cells = p.cells ?? [];
  const [cc, cr] = p.caret ?? [0, 0];
  const flat = cells.flatMap((row, r) => (row ?? []).flatMap((cell, c) => (cell.sign?.length === 1 ? [{ x: c, y: r, ch: cell.sign, kind: 0, decimal: cell.mark === "," || cell.mark === "." }] : [])));
  const tint = gridTint(flat, places);
  const at = (n: number) => Array.from({ length: n + 1 }, (_, i) => i * size);
  const sq = (c: number, r: number): Square => cells[r]?.[c] ?? {};
  return (
    <div className="karofeld">
      <svg data-look={look} viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none">
        {Array.from({ length: rows }, (_, r) =>
          Array.from({ length: cols }, (_, c) => {
            const cell = sq(c, r);
            return (
              <rect
                key={`f${c},${r}`}
                className="cell"
                data-col={c}
                data-row={r}
                x={c * size}
                y={r * size}
                width={size}
                height={size}
                fill={cell.fill ?? "transparent"}
                stroke="none"
                onPointerDown={onSquare ? () => onSquare(c, r) : undefined}
              />
            );
          }),
        )}
        {look === "iso" ? (
          <g className="mesh">
            {isoLines(p).map((ln, i) => (
              <line key={i} x1={ln[0]} y1={ln[1]} x2={ln[2]} y2={ln[3]} />
            ))}
          </g>
        ) : look === "punkte" ? (
          Array.from({ length: rows }, (_, r) =>
            Array.from({ length: cols }, (_, c) => <circle key={`d${c},${r}`} className="dot" cx={(c + 0.5) * size} cy={(r + 0.5) * size} r={size * 0.12} />),
          )
        ) : (
          <g className="mesh">
            {at(cols).map((x) => (
              <line key={`v${x}`} x1={x} x2={x} y1={0} y2={h} />
            ))}
            {at(rows).map((y) => (
              <line key={`h${y}`} y1={y} y2={y} x1={0} x2={w} />
            ))}
          </g>
        )}
        {look === "kreise" &&
          Array.from({ length: rows }, (_, r) =>
            Array.from({ length: cols }, (_, c) => <circle key={`k${c},${r}`} className="ring" cx={(c + 0.5) * size} cy={(r + 0.5) * size} r={size * 0.38} />),
          )}
        {Array.from({ length: rows }, (_, r) =>
          Array.from({ length: cols }, (_, c) => {
            const cell = sq(c, r);
            const hit = cell.sign?.length === 1 ? tint.get(`${c},${r}`) : undefined;
            const edges = cell.thick ?? [];
            const sides: [boolean, number, number, number, number][] = [
              [!!edges[0], c * size, r * size, (c + 1) * size, r * size],
              [!!edges[1], (c + 1) * size, r * size, (c + 1) * size, (r + 1) * size],
              [!!edges[2], c * size, (r + 1) * size, (c + 1) * size, (r + 1) * size],
              [!!edges[3], c * size, r * size, c * size, (r + 1) * size],
            ];
            return (
              <g key={`s${c},${r}`}>
                {sides.map(([on, x1, y1, x2, y2], i) => on && <line key={i} className="thick" x1={x1} y1={y1} x2={x2} y2={y2} />)}
                {cell.line && <line className="loesung" x1={(c + 0.15) * size} x2={(c + 0.85) * size} y1={(r + 0.78) * size} y2={(r + 0.78) * size} />}
                {cell.sign && (
                  <text x={(c + 0.5) * size} y={(r + 0.5) * size} fontFamily="Andika" fontSize={fontOf(size)} textAnchor="middle" dominantBaseline="central" fill="#222" data-place={hit?.place} style={hit ? { fill: hit.color } : undefined}>
                    {cell.sign.length > 1 ? <SvgInk text={cell.sign} /> : cell.sign}
                    {cell.mark ?? ""}
                  </text>
                )}
              </g>
            );
          }),
        )}
        <rect className="caret" data-col={cc} data-row={cr} x={cc * size + 0.4} y={cr * size + 0.4} width={size - 0.8} height={size - 0.8} />
      </svg>
    </div>
  );
}
