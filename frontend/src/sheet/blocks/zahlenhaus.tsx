// Draws one Zahlenhaus block.

import { sane as saneHouse, made as housed, layout as houseLayout, numberSize } from "../../zahlenhaus";
import type { ZahlenhausBlock } from "../tasks";

// A Zahlenhaus: its houses in columns, in its own units. A house is a roof over two boxes a floor, each floor's two
// boxes adding up to the roof. A wrong floor shows no answer, and its house is marked `wrong`.
export function Zahlenhaus({ block, solved }: { block: ZahlenhausBlock; k: number; solved: boolean }) {
  const p = saneHouse(block.props);
  const { houses } = housed(p);
  const { S, houseW, houseH, gap, vbW, vbH } = houseLayout(p);
  return (
    <div className={`zahlenhaus${solved ? " solved" : ""}`}>
      <svg viewBox={`-0.5 -0.5 ${vbW} ${vbH}`} preserveAspectRatio="xMidYMin meet">
        {houses.map((h, i) => {
          const [x0, y0] = [(i % p.columns) * (houseW + gap), Math.floor(i / p.columns) * (houseH + gap)];
          // The number of box j, drawn when it is given, or in the answer key when its floor is not wrong.
          const numberOf = (j: number, floor: number, x: number, y: number) => {
            const shows = h.given[j] || (solved && !h.wrong[floor]);
            return shows && (
              <text x={x} y={y} fontSize={numberSize(String(h.numbers[j]).length, S, 0.55 * S)} textAnchor="middle" dominantBaseline="central"
                fill={h.given[j] ? "#222" : "#c0392b"} className={h.given[j] ? "given" : "answer"}>{h.numbers[j]}</text>
            );
          };
          return (
            <g key={i} className={`house${h.wrong.some(Boolean) ? " wrong" : ""}`} data-house={i}>
              <g className="box" data-box={0}>
                <polygon points={`${x0},${y0 + S} ${x0 + S},${y0} ${x0 + 2 * S},${y0 + S}`} fill="white" stroke="#222" strokeWidth={0.4} />
                {h.given[0] || solved ? (
                  <text x={x0 + S} y={y0 + 0.65 * S} fontSize={numberSize(String(h.numbers[0]).length, S, 0.45 * S)} textAnchor="middle" dominantBaseline="central"
                    fill={h.given[0] ? "#222" : "#c0392b"} className={h.given[0] ? "given" : "answer"}>{h.numbers[0]}</text>
                ) : null}
              </g>
              {h.wrong.map((wrong, f) => {
                const [yf, left, right] = [y0 + (f + 1) * S, 1 + 2 * f, 2 + 2 * f];
                return [
                  <g key={left} className={`box${wrong ? " wrong" : ""}`} data-box={left}>
                    <rect x={x0} y={yf} width={S} height={S} fill="white" stroke="#222" strokeWidth={0.4} />
                    {numberOf(left, f, x0 + S / 2, yf + S / 2)}
                  </g>,
                  <g key={right} className={`box${wrong ? " wrong" : ""}`} data-box={right}>
                    <rect x={x0 + S} y={yf} width={S} height={S} fill="white" stroke="#222" strokeWidth={0.4} />
                    {numberOf(right, f, x0 + 1.5 * S, yf + S / 2)}
                  </g>,
                ];
              })}
            </g>
          );
        })}
      </svg>
    </div>
  );
}
