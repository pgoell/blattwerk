// The sheet document and how a page of it draws, shared by the editor and the list's thumbnails.
import type { CSSProperties } from "react";

// One page's blocks, as the sheet document stores them: mm from the page's top-left corner. `mark` is the numbering
// before a block: "1.", "a)" or "(1)", which count on through the sheet, or a symbol's code.
export type Box = { id: string; x: number; y: number; w: number; h: number; z: number; locked: boolean; mark?: string };
export type Kind = "rect" | "rounded" | "circle" | "line" | "arrow";
export type Corner = "nw" | "ne" | "sw" | "se";
export type Align = "left" | "center" | "right";
export type Font = keyof typeof FONTS;
export type Ruling = keyof typeof RULINGS;
// Sheets saved before text had these settings lack them: a text is then Andika, black, with lines 1.3 apart.
export type TextProps = { text: string; size: number; align: Align; font?: Font; bold?: boolean; italic?: boolean; underline?: boolean; color?: string; spacing?: number };
export type TextBlock = Box & { type: "text"; props: TextProps };
// A line or arrow runs from the corner `from` of its box to the opposite one.
export type ShapeBlock = Box & { type: "shape"; props: { kind: Kind; fill: string; stroke: string; strokeWidth: number; from?: Corner } };
// As many rows as fit the block's height are drawn.
export type RulingBlock = Box & { type: "ruling"; props: { kind: Ruling; color: string } };
export type NameBlock = Box & { type: "name"; props: Record<string, never> };
export type PointsBlock = Box & { type: "points"; props: { max: number } };
export type SymbolBlock = Box & { type: "symbol"; props: { code: string } };
// `ratio` is the picture's width over its height; `cut` the share cropped off its left, top, right and bottom.
export type ImageBlock = Box & { type: "image"; props: { upload: number; ratio: number; cut: number[] } };
export type Block = TextBlock | ShapeBlock | RulingBlock | NameBlock | PointsBlock | SymbolBlock | ImageBlock;
export type Axis = "x" | "y";
// The teacher's own guide lines, in mm.
export type Guides = Record<Axis, number[]>;
// A page can have guide lines of its own, beside the sheet's, and a grid of its own in place of the sheet's.
export type Page = { blocks: Block[]; guides?: Guides; grid?: number };
// The pages, and what every page shares: guide lines and the grid's cell in mm (0 for none).
export type Doc = { pages: Page[]; guides: Guides; grid: number };
// The server counts a sheet's saved documents in `version`.
export type Sheet = { id: number; title: string; updated: string; version: number; doc: Doc };

export const W = 210;
export const H = 297;
export const PT = 25.4 / 72; // mm per point
// Self-hosted, all under the SIL Open Font License: Andika for print, Playwrite for the four school scripts.
export const FONTS = {
  andika: ["Druckschrift", "Andika"],
  grund: ["Grundschrift", "Playwrite DE Grund Variable"],
  va: ["Vereinfachte Ausgangsschrift", "Playwrite DE VA Variable"],
  sas: ["Schulausgangsschrift", "Playwrite DE SAS Variable"],
  la: ["Lateinische Ausgangsschrift", "Playwrite DE LA Variable"],
};
// One row of each ruling: its height, and where its lines lie in mm from the row's top; Karo has squares instead.
// Lineatur 1 to 4 follow DIN 16552-1: four lines 5 mm apart, four lines 4 mm apart, a band of 3.5 mm, single lines
// 10 mm apart. The gap to the next row's lines (5, 4 and 8 mm) lies half above and half below, so blocks stack.
// In Lineatur 1 and 2 that gap is as wide as a zone, so the middle band is tinted, as in the schoolbooks: without
// it no one could tell where a row begins.
export const RULINGS = {
  l1: { name: "Lineatur 1 (Klasse 1)", row: 20, at: [2.5, 7.5, 12.5, 17.5], band: 5 },
  l2: { name: "Lineatur 2 (Klasse 2)", row: 16, at: [2, 6, 10, 14], band: 4 },
  l3: { name: "Lineatur 3 (Klasse 3)", row: 11.5, at: [4, 7.5], band: 0 },
  l4: { name: "Lineatur 4 (Klasse 4)", row: 10, at: [10], band: 0 },
  lines: { name: "Linien, 8 mm", row: 8, at: [8], band: 0 },
  k5: { name: "Karo 5 mm", row: 5, at: undefined, band: 0 },
  k7: { name: "Karo 7 mm", row: 7, at: undefined, band: 0 },
};
// The numbering styles, each from a count that starts at 1.
export const MARKS: Record<string, (n: number) => string> = {
  "1.": (n) => `${n}.`,
  "a)": (n) => `${String.fromCharCode(97 + ((n - 1) % 26))})`,
  "(1)": (n) => `(${n})`,
};
export const EMPTY: Doc = { pages: [{ blocks: [] }], guides: { x: [], y: [] }, grid: 0 };
// The editor's last save. The list waits for it, so it shows the sheet as it was left.
export const last = { save: Promise.resolve() as Promise<unknown> };

// Templates saved before sheets had pages hold one page's blocks.
export const read = ({ pages, blocks, guides, grid }: Doc & { blocks?: Block[] }): Doc => ({ pages: pages ?? [{ blocks: blocks! }], guides, grid });
export const isLine = (b: Block): b is ShapeBlock => b.type === "shape" && (b.props.kind === "line" || b.props.kind === "arrow");
// Whether a line's start, or its end, sits at the bottom (axis 0) or the right (axis 1) of its box.
export const far = (b: ShapeBlock, axis: 0 | 1, end: boolean) => ((b.props.from ?? "nw")[axis] === "se"[axis]) !== end;
export const symbol = (code: string) => `/openmoji/${code}.svg`;
// How many rows of its ruling fit a block. Moveable's pixels leave a height a hair short of a full row.
export const rowsOf = (b: RulingBlock) => Math.floor(b.h / RULINGS[b.props.kind].row + 0.05);
export const textStyle = (p: TextProps, k: number): CSSProperties => ({
  fontFamily: FONTS[p.font ?? "andika"][1],
  fontSize: p.size * PT * k,
  fontWeight: p.bold ? 700 : 400,
  fontStyle: p.italic ? "italic" : "normal",
  textDecoration: p.underline ? "underline" : "none",
  textAlign: p.align,
  color: p.color,
  lineHeight: p.spacing ?? 1.3,
});
// The number before each numbered block. Blocks count in reading order, page after page; after each "1." the
// letters and the bracketed numbers start over, so tasks can have parts.
export function numbers(doc: Doc) {
  const out = new Map<string, string>();
  const count: Record<string, number> = {};
  for (const page of doc.pages)
    for (const b of [...page.blocks].sort((a, b) => a.y - b.y || a.x - b.x)) {
      if (!b.mark || !MARKS[b.mark]) continue;
      if (b.mark === "1.") count["a)"] = count["(1)"] = 0;
      count[b.mark] = (count[b.mark] ?? 0) + 1;
      out.set(b.id, MARKS[b.mark](count[b.mark]));
    }
  return out;
}

export function Shape({ block, k }: { block: ShapeBlock; k: number }) {
  const { kind, fill, stroke, strokeWidth } = block.props;
  if (isLine(block)) {
    // Drawn from the start corner along its own axis; a wide unseen stroke is what a finger grabs.
    const [x, y] = [far(block, 1, false) ? block.w : 0, far(block, 0, false) ? block.h : 0];
    const angle = (Math.atan2(block.h - 2 * y, block.w - 2 * x) * 180) / Math.PI;
    const length = Math.hypot(block.w, block.h);
    const head = kind === "arrow" ? 2 + strokeWidth * 3 : 0;
    return (
      <svg>
        <g transform={`scale(${k}) translate(${x} ${y}) rotate(${angle})`} stroke={stroke} strokeWidth={strokeWidth} fill={stroke}>
          <line x2={length} stroke="transparent" strokeWidth={10} />
          <line x2={length - head} />
          {head > 0 && <polygon stroke="none" points={`${length},0 ${length - head},${-head / 2} ${length - head},${head / 2}`} />}
        </g>
      </svg>
    );
  }
  return (
    <div
      style={{
        background: fill,
        border: `${strokeWidth * k}px solid ${stroke}`,
        borderRadius: kind === "circle" ? "50%" : kind === "rounded" ? 4 * k : 0,
      }}
    />
  );
}

// Drawn in mm: the SVG's own scale takes it to the block's size.
function Lines({ block }: { block: RulingBlock }) {
  const { row, at, band } = RULINGS[block.props.kind];
  const rows = rowsOf(block);
  const cols = Math.floor(block.w / row + 0.05);
  const each = (n: number) => Array.from({ length: n }, (_, i) => i * row);
  const ys = at ? each(rows).flatMap((top) => at.map((y) => top + y)) : each(rows + 1);
  return (
    <div>
      <svg className="ruling" viewBox={`0 0 ${block.w} ${block.h}`} stroke={block.props.color} strokeWidth={0.2}>
        {/* The middle band lies between a row's second and third line. */}
        {band > 0 && each(rows).map((top) => <rect key={top} y={top + at![1]} width={block.w} height={band} fill={block.props.color} fillOpacity={0.12} stroke="none" />)}
        {ys.map((y) => (
          <line key={y} x2={at ? block.w : cols * row} y1={y} y2={y} />
        ))}
        {!at && each(cols + 1).map((x) => <line key={x} x1={x} x2={x} y2={rows * row} />)}
      </svg>
    </div>
  );
}

// What a block shows, at `k` pixels per mm. Sizes inside a block are in em of a font size set to the scale.
export function Draw({ block, k }: { block: Block; k: number }) {
  if (block.type === "text") return <p style={textStyle(block.props, k)}>{block.props.text}</p>;
  if (block.type === "shape") return <Shape block={block} k={k} />;
  if (block.type === "ruling") return <Lines block={block} />;
  if (block.type === "symbol") return <img src={symbol(block.props.code)} alt="" draggable={false} />;
  if (block.type === "name")
    return (
      <div className="fields" style={{ fontSize: 12 * PT * k }}>
        {["Name", "Datum", "Klasse"].map((field) => (
          <span key={field}>
            {field}:<i />
          </span>
        ))}
      </div>
    );
  if (block.type === "points")
    return (
      <div className="points" style={{ fontSize: 12 * PT * k }}>
        / {block.props.max} Punkte
      </div>
    );
  const [l, t, r, b] = block.props.cut;
  const [w, h] = [1 - l - r, 1 - t - b];
  return (
    <div className="picture">
      <img
        src={`/api/uploads/${block.props.upload}`}
        alt=""
        draggable={false}
        style={{ width: `${100 / w}%`, height: `${100 / h}%`, left: `${(-100 * l) / w}%`, top: `${(-100 * t) / h}%` }}
      />
    </div>
  );
}

// A block's numbering stands to the left of its box, so the box keeps its place and its snap lines. `n` is the
// number of a counted block; a symbol has none.
export function Mark({ block, k, n }: { block: Block; k: number; n?: string }) {
  if (!block.mark) return null;
  const style = textStyle(block.type === "text" ? block.props : { text: "", size: 14, align: "left" }, k);
  return (
    <b className="mark" style={{ ...style, textDecoration: "none" }}>
      {n ?? <img src={symbol(block.mark)} alt="" />}
    </b>
  );
}

// Page one, drawn small at `k` pixels per mm.
export function Thumb({ doc, k }: { doc: Doc; k: number }) {
  const ns = numbers(read(doc));
  return (
    <div className="thumb" style={{ width: W * k, height: H * k }}>
      {read(doc).pages[0].blocks.map((b) => (
        <div key={b.id} className="block" style={{ left: b.x * k, top: b.y * k, width: b.w * k, height: b.h * k, zIndex: b.z }}>
          <Draw block={b} k={k} />
          <Mark block={b} k={k} n={ns.get(b.id)} />
        </div>
      ))}
    </div>
  );
}
