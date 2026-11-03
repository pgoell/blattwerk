// A formula drawn as text, so the PDF keeps it as letters and the size follows the font.

import type { ReactNode } from "react";
import { PT } from "../height";
import { asFormula, parse, sane, splitFormula, type Node } from "../formula";
import type { FormulaBlock } from "./doc";

function draw(n: Node): ReactNode {
  switch (n.k) {
    case "text":
      return n.s;
    case "row":
      return <span className="f-row">{n.xs.map((x, i) => <span key={i}>{draw(x)}</span>)}</span>;
    case "frac":
      return (
        <span className="f-frac">
          <span className="f-num">{draw(n.a)}</span>
          <span className="f-den">{draw(n.b)}</span>
        </span>
      );
    case "mixed":
      return (
        <span className="f-mixed">
          <span>{n.n}</span>
          {draw({ k: "frac", a: n.a, b: n.b })}
        </span>
      );
    case "sup":
      return (
        <span className="f-script">
          <span>{draw(n.a)}</span>
          <span className="f-sup">{draw(n.e)}</span>
        </span>
      );
    case "sub":
      return (
        <span className="f-script">
          <span>{draw(n.a)}</span>
          <span className="f-sub">{draw(n.e)}</span>
        </span>
      );
    case "both":
      return (
        <span className="f-script">
          <span>{draw(n.a)}</span>
          <span className="f-scripts">
            <span>{draw(n.sup)}</span>
            <span>{draw(n.sub)}</span>
          </span>
        </span>
      );
    case "sqrt":
      return (
        <span className="f-root">
          <span className="f-sign">{"\u221A"}</span>
          <span className="f-body">{draw(n.a)}</span>
        </span>
      );
    case "blank":
      return <span className="f-blank" />;
  }
}

export function Formula({ source }: { source: string }) {
  return (
    <span className="formula" data-formula={source}>
      {draw(parse(source))}
    </span>
  );
}

// A text that may hold `\f{...}` among its words. With none, the words are unchanged.
export function FormulaText({ text }: { text: string }) {
  const bits = splitFormula(text);
  if (bits.length === 1 && bits[0].formula === undefined) return <>{text}</>;
  return (
    <>
      {bits.map((bit, i) => (bit.formula !== undefined ? <Formula key={i} source={bit.formula} /> : <span key={i}>{bit.text}</span>))}
    </>
  );
}

export function FormulaBox({ block, k }: { block: FormulaBlock; k: number }) {
  const p = sane(block.props);
  return (
    <div className={`formula-box ${p.align}`} style={{ fontSize: p.size * PT * k, color: p.color }}>
      <Formula source={p.source} />
    </div>
  );
}

// A written Rechnen cell, drawn as svg text so the PDF keeps the letters. `em` is the font size in the svg's units.
type Mark = { s: string; x: number; y: number; em: number } | { bar: true; x: number; y: number; w: number };
type Laid = { w: number; h: number; draw: (x: number, y: number, marks: Mark[]) => void };

function laid(n: Node, em: number): Laid {
  if (n.k === "text") {
    const w = Math.max([...n.s].length, 1) * 0.6 * em;
    return { w, h: em, draw: (x, y, marks) => marks.push({ s: n.s, x, y: y + em * 0.75, em }) };
  }
  if (n.k === "blank") {
    const w = 1.6 * em;
    return { w, h: em, draw: (x, y, marks) => marks.push({ bar: true, x, y: y + em * 0.9, w }) };
  }
  if (n.k === "row") {
    const parts = n.xs.map((x) => laid(x, em));
    const gap = 0.12 * em;
    const w = parts.reduce((sum, p) => sum + p.w, 0) + gap * Math.max(0, parts.length - 1);
    const h = Math.max(em, ...parts.map((p) => p.h), 0);
    return {
      w,
      h,
      draw: (x, y, marks) => {
        let at = x;
        for (const p of parts) {
          p.draw(at, y + (h - p.h) / 2, marks);
          at += p.w + gap;
        }
      },
    };
  }
  if (n.k === "frac") {
    const a = laid(n.a, em * 0.7);
    const b = laid(n.b, em * 0.7);
    const gap = 0.16 * em;
    const w = Math.max(a.w, b.w) + 0.24 * em;
    return {
      w,
      h: a.h + b.h + gap,
      draw: (x, y, marks) => {
        a.draw(x + (w - a.w) / 2, y, marks);
        marks.push({ bar: true, x, y: y + a.h + gap * 0.35, w });
        b.draw(x + (w - b.w) / 2, y + a.h + gap, marks);
      },
    };
  }
  if (n.k === "mixed") {
    const whole = laid({ k: "text", s: n.n }, em);
    const frac = laid({ k: "frac", a: n.a, b: n.b }, em);
    const gap = 0.08 * em;
    const h = Math.max(whole.h, frac.h);
    return {
      w: whole.w + gap + frac.w,
      h,
      draw: (x, y, marks) => {
        whole.draw(x, y + (h - whole.h) / 2, marks);
        frac.draw(x + whole.w + gap, y + (h - frac.h) / 2, marks);
      },
    };
  }
  if (n.k === "sup" || n.k === "sub") {
    const base = laid(n.a, em);
    const e = laid(n.e, em * 0.7);
    const h = base.h + e.h * 0.3;
    return {
      w: base.w + e.w,
      h,
      draw: (x, y, marks) => {
        base.draw(x, y + (n.k === "sup" ? e.h * 0.3 : 0), marks);
        e.draw(x + base.w, y + (n.k === "sup" ? 0 : base.h * 0.45), marks);
      },
    };
  }
  if (n.k === "both") {
    const base = laid(n.a, em);
    const sup = laid(n.sup, em * 0.7);
    const sub = laid(n.sub, em * 0.7);
    return {
      w: base.w + Math.max(sup.w, sub.w),
      h: sup.h + sub.h + base.h * 0.2,
      draw: (x, y, marks) => {
        base.draw(x, y + sup.h * 0.4, marks);
        sup.draw(x + base.w, y, marks);
        sub.draw(x + base.w, y + sup.h, marks);
      },
    };
  }
  const body = laid(n.a, em);
  const sign = laid({ k: "text", s: "\u221A" }, em);
  return {
    w: sign.w + body.w,
    h: body.h + 0.12 * em,
    draw: (x, y, marks) => {
      sign.draw(x, y + 0.12 * em, marks);
      marks.push({ bar: true, x: x + sign.w * 0.7, y: y + 0.1 * em, w: body.w + 0.12 * em });
      body.draw(x + sign.w, y + 0.12 * em, marks);
    },
  };
}

export function FormulaCell({ source, x, y, side, em }: { source: string; x: number; y: number; side: number; em: number }) {
  const box = laid(parse(source), em);
  const marks: Mark[] = [];
  box.draw(x + (side - box.w) / 2, y + (side - box.h) / 2, marks);
  return (
    <g className="formula">
      {marks.map((m, i) =>
        "bar" in m ? (
          <line key={i} x1={m.x} x2={m.x + m.w} y1={m.y} y2={m.y} stroke="currentColor" strokeWidth={Math.max(em * 0.06, 0.12)} />
        ) : (
          <text key={i} x={m.x} y={m.y} fontSize={m.em} fill="currentColor">
            {m.s}
          </text>
        ),
      )}
    </g>
  );
}
