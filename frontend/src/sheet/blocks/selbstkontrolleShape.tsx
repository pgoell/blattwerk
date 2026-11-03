// The four ways a shuffled Selbstkontrolle can look, besides the tick list: a plain box, a snake, a caterpillar, a train.
import type { MixLook } from "../../selbstkontrolle";
import { shapeBox, wound, type ShapeLook } from "../../selbstkontrolle/shape";

const font = (text: string, full: number) => (text.length > 4 ? full * 0.62 : text.length > 2 ? full * 0.78 : full);

export function Mixed({ look, items }: { look: MixLook; items: string[] }) {
  if (look === "box") return <ul className="box">{items.map((text, i) => <li key={i}>{text}</li>)}</ul>;
  if (look === "ticks")
    return (
      <ul className="mixed">
        {items.map((text, i) => (
          <li key={i}>
            <span className="tick" />
            {text}
          </li>
        ))}
      </ul>
    );
  return <Shape look={look} items={items} />;
}

function Shape({ look, items }: { look: ShapeLook; items: string[] }) {
  if (!items.length) return null;
  if (look === "train") return <Train items={items} />;
  const box = shapeBox(look, items.length);
  const r = look === "caterpillar" ? 13 : 16;
  const spots = wound(items.length, box.cols, box.dx, box.dy, box.pad + box.dx / 2, box.pad + box.dy / 2);
  const path = spots.map((p, i) => `${i ? "L" : "M"}${p[0]} ${p[1]}`).join(" ");
  return (
    <svg className={`shape ${look}`} viewBox={`0 0 ${box.w} ${box.h}`} role="img" aria-label={look === "snake" ? "Zahlenschlange" : "Raupe"}>
      <path d={path} fill="none" stroke="#222" strokeWidth={look === "caterpillar" ? 8 : 2} strokeLinecap="round" />
      {items.map((text, i) => (
        <g key={i}>
          <circle className="bubble" cx={spots[i][0]} cy={spots[i][1]} r={r} fill="white" stroke="#222" strokeWidth={i === 0 && look === "caterpillar" ? 1.8 : 1.2} />
          {look === "caterpillar" && i === 0 && (
            <>
              <circle className="eye" cx={spots[i][0] - 4} cy={spots[i][1] - 3} r={1.6} fill="#222" />
              <circle className="eye" cx={spots[i][0] + 4} cy={spots[i][1] - 3} r={1.6} fill="#222" />
            </>
          )}
          <text x={spots[i][0]} y={spots[i][1] + (look === "caterpillar" && i === 0 ? 3 : 0)} textAnchor="middle" dominantBaseline="central" fontFamily="Andika" fontSize={font(text, 12)}>
            {text}
          </text>
        </g>
      ))}
    </svg>
  );
}

function Train({ items }: { items: string[] }) {
  const box = shapeBox("train", items.length);
  return (
    <svg className="shape train" viewBox={`0 0 ${box.w} ${box.h}`} role="img" aria-label="Zug">
      {items.map((text, i) => {
        const row = Math.floor(i / box.cols);
        const col = i % box.cols;
        const x = box.pad + col * box.dx;
        const y = box.pad + row * box.dy;
        const engine = i === 0;
        return (
          <g key={i}>
            {col > 0 && <line x1={x - 8} y1={y + 28} x2={x} y2={y + 28} stroke="#222" strokeWidth={1.4} />}
            {engine && <rect x={x + 40} y={y + 2} width={14} height={12} fill="white" stroke="#222" strokeWidth={1.2} />}
            {engine && <rect x={x + 44} y={y - 4} width={5} height={7} fill="white" stroke="#222" strokeWidth={1.2} />}
            <rect x={x + 2} y={y + 12} width={engine ? 54 : 52} height={22} rx={2} fill="white" stroke="#222" strokeWidth={1.4} />
            <circle cx={x + 14} cy={y + 40} r={5} fill="white" stroke="#222" strokeWidth={1.2} />
            <circle cx={x + 44} cy={y + 40} r={5} fill="white" stroke="#222" strokeWidth={1.2} />
            <text x={x + (engine ? 29 : 28)} y={y + 23} textAnchor="middle" dominantBaseline="central" fontFamily="Andika" fontSize={font(text, 12)}>
              {text}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
