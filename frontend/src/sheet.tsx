// The sheet document and how a page of it draws, shared by the editor, the list's thumbnails and the PDF.
import type { CSSProperties, ReactNode } from "react";

// One page's blocks, as the sheet document stores them: mm from the page's top-left corner. `mark` is the numbering
// before a block: a counting one such as "1.", "a)" or "(1)", or a symbol's code.
export type Box = { id: string; x: number; y: number; w: number; h: number; z: number; locked: boolean; mark?: string; group?: string[] };
export type Kind = "rect" | "rounded" | "circle" | "line" | "arrow";
export type Corner = "nw" | "ne" | "sw" | "se";
export type Align = "left" | "center" | "right";
export type Font = keyof typeof FONTS;
export type Ruling = keyof typeof RULINGS;
export type Valign = "top" | "middle" | "bottom";
// Sheets saved before text had these settings lack them: a text is then Andika, black, with lines 1.3 apart.
// A text has what a shape has, as a PowerPoint text box does: a fill and a border ("none" or absent for neither,
// the border 0.5 mm wide unless set), dashes, and round corners with `kind`.
export type TextProps = { text: string; size: number; align: Align; font?: Font; bold?: boolean; italic?: boolean; underline?: boolean; color?: string; spacing?: number; valign?: Valign; kind?: Kind; fill?: string; stroke?: string; strokeWidth?: number; dash?: "dashed" | "dotted" };
export type TextBlock = Box & { type: "text"; props: TextProps };
// A shape can hold text: centred and in the middle unless set otherwise. A line or arrow runs from the corner
// `from` of its box to the opposite one. It can have a tick at each end and say how long it is, on the sheet
// ("show") or on the answer key alone ("key").
export type ShapeBlock = Box & { type: "shape"; props: Partial<TextProps> & { kind: Kind; fill: string; stroke: string; strokeWidth: number; from?: Corner; ticks?: boolean; label?: "show" | "key" } };
// As many rows as fit the block's height are drawn. `text` is written on the rows, on Karo a character to a
// square, and grey with `trace` so the children can write over it. Karo is always in print.
export type RulingBlock = Box & { type: "ruling"; props: { kind: Ruling; color: string; text?: string; font?: Font; trace?: boolean } };
export type NameBlock = Box & { type: "name"; props: Record<string, never> };
export type PointsBlock = Box & { type: "points"; props: { max: number } };
export type SymbolBlock = Box & { type: "symbol"; props: { code: string } };
// `ratio` is the picture's width over its height; `cut` the share cropped off its left, top, right and bottom.
export type ImageBlock = Box & { type: "image"; props: { upload: number; ratio: number; cut: number[] } };
export type Op = keyof typeof SIGNS;
// The lowest and the highest digit a place may hold.
export type Range = [number, number];
// A written exercise on squared paper. A cell is [column, row, character, kind], a line [from column, to column,
// above row, kind]; kind 0 is printed on the sheet, 1 is the answer key's and 2 a small carry of the answer key's.
export type Grid = { cols: number; rows: number; cells: [number, number, string, number][]; lines: [number, number, number, number][] };
// `hide` is the number a gap stands for, the result when absent. `rest` is what a division leaves.
export type Exercise = { op: Op; a: number; b: number; result: number; rest: number; hide?: "a" | "b"; grid?: Grid };
// The generator's limits, as the server takes them: `a` and `b` hold the digits each number may have, units first.
export type Limits = {
  ops: Op[];
  max: number;
  a: Range[];
  b: Range[];
  carry: "none" | "required" | "either";
  rest: boolean;
  format: "row" | "gap" | "written";
  count: number;
  seed: number;
};
// What the generator made of the limits. With fewer exercises than asked for, `loosen` names the limits in the way.
export type Made = { exercises: Exercise[]; loosen: string[] | null };
// `numbering` counts the exercises of the block; `size` is the font size of a row or a gap in points.
export type MathsProps = Limits & Made & { columns: number; size: number; numbering?: string };
export type MathsBlock = Box & { type: "maths"; props: MathsProps };
export type Block = TextBlock | ShapeBlock | RulingBlock | NameBlock | PointsBlock | SymbolBlock | ImageBlock | MathsBlock;
export type Axis = "x" | "y";
// The teacher's own guide lines, in mm.
export type Guides = Record<Axis, number[]>;
// A page can have guide lines of its own, beside the sheet's, and a grid and a format of its own in place of the
// sheet's.
export type Page = { blocks: Block[]; guides?: Guides; grid?: number; landscape?: boolean };
// The pages, and what every page shares: guide lines, the grid's cell in mm (0 for none), and whether the A4 lies
// on its side.
export type Doc = { pages: Page[]; guides: Guides; grid: number; landscape?: boolean };
// The server counts a sheet's saved documents in `version`.
export type Sheet = { id: number; title: string; updated: string; version: number; doc: Doc };

// A page's width and height in mm: A4, upright or on its side.
export const sizeOf = (doc: Doc, n: number) => ((doc.pages[n].landscape ?? doc.landscape) ? [297, 210] : [210, 297]);
// The margin a new block keeps, and a ruling that fills the page.
export const MARGIN = 15;
export const PT = 25.4 / 72; // mm per point
// Self-hosted, all under the SIL Open Font License: Andika for print, Playwrite for the four school scripts.
// The number is how far a font's baseline lies below the middle of a line of text, in em: half of its ascent less
// its descent. Text on a ruling needs it to stand on the line.
export const FONTS = {
  andika: ["Druckschrift", "Andika", 0.415],
  grund: ["Grundschrift", "Playwrite DE Grund Variable", 0.4545],
  va: ["Vereinfachte Ausgangsschrift", "Playwrite DE VA Variable", 0.46],
  sas: ["Schulausgangsschrift", "Playwrite DE SAS Variable", 0.4515],
  la: ["Lateinische Ausgangsschrift", "Playwrite DE LA Variable", 0.4545],
} as const;
// One row of each ruling: its height, and where its lines lie in mm from the row's top; Karo has squares instead.
// Lineatur 1 to 4 follow DIN 16552-1: four lines 5 mm apart, four lines 4 mm apart, a band of 3.5 mm, single lines
// 10 mm apart. The gap to the next row's lines (5, 4 and 8 mm) lies half above and half below, so blocks stack.
// In Lineatur 1 and 2 that gap is as wide as a zone, so the middle band is tinted, as in the schoolbooks: without
// it no one could tell where a row begins.
// Text stands on `base`, in a font of `size` mm. Every font's small letters are half its size high, so they fill
// the band of Lineatur 1 to 3; single lines have no band and take small letters 0.3 of a row high. On Karo a
// character is 0.75 of its square, as in a written exercise.
export const RULINGS = {
  l1: { name: "Lineatur 1 (Klasse 1)", row: 20, at: [2.5, 7.5, 12.5, 17.5], band: 5, base: 12.5, size: 10 },
  l2: { name: "Lineatur 2 (Klasse 2)", row: 16, at: [2, 6, 10, 14], band: 4, base: 10, size: 8 },
  l3: { name: "Lineatur 3 (Klasse 3)", row: 11.5, at: [4, 7.5], band: 0, base: 7.5, size: 7 },
  l4: { name: "Lineatur 4 (Klasse 4)", row: 10, at: [10], band: 0, base: 10, size: 6 },
  lines: { name: "Linien, 8 mm", row: 8, at: [8], band: 0, base: 8, size: 4.8 },
  k5: { name: "Karo 5 mm", row: 5, at: undefined, band: 0, base: 0, size: 3.75 },
  k7: { name: "Karo 7 mm", row: 7, at: undefined, band: 0, base: 0, size: 5.25 },
};
// The signs as German schools write them.
export const SIGNS = { "+": "+", "-": "−", "*": "·", "/": ":" };
// The side of a square of a written exercise, in mm.
export const KARO = 5;
// A numbering counts in numbers, "1", or letters, "a", and has one of these looks; "#o" is a ring around it.
export const LOOKS = ["#", "#.", "#)", "(#)", "#o"];
export const lookOf = (mark: string) => mark.replace(/[1a]/, "#");
// Whether a mark counts; a symbol's code does not.
export const counts = (mark?: string): mark is string => !!mark && LOOKS.includes(lookOf(mark));
export const EMPTY: Doc = { pages: [{ blocks: [] }], guides: { x: [], y: [] }, grid: 0 };
// The editor's last save. The list waits for it, so it shows the sheet as it was left.
export const last = { save: Promise.resolve() as Promise<unknown> };

// Templates saved before sheets had pages hold one page's blocks.
export const read = ({ pages, blocks, guides, grid, landscape }: Doc & { blocks?: Block[] }): Doc => ({ pages: pages ?? [{ blocks: blocks! }], guides, grid, landscape });
export const isLine = (b: Block): b is ShapeBlock => b.type === "shape" && (b.props.kind === "line" || b.props.kind === "arrow");
// Whether a line's start, or its end, sits at the bottom (axis 0) or the right (axis 1) of its box.
export const far = (b: ShapeBlock, axis: 0 | 1, end: boolean) => ((b.props.from ?? "nw")[axis] === "se"[axis]) !== end;
// The text and the frame of a text, or of a shape that is no line.
export function boxed(b: Block): TextProps | undefined {
  if (b.type === "text") return b.props;
  // `isLine` tells the compiler that every shape it turns down is no shape, so the props are read first.
  const props = b.type === "shape" ? b.props : undefined;
  if (props && !isLine(b)) return { text: "", size: 14, align: "center", valign: "middle", ...props };
}
export const symbol = (code: string) => `/openmoji/${code}.svg`;
// How many rows of its ruling fit a block. Moveable's pixels leave a height a hair short of a full row.
export const rowsOf = (b: RulingBlock) => Math.floor(b.h / RULINGS[b.props.kind].row + 0.05);
export const colsOf = (b: RulingBlock) => Math.floor(b.w / RULINGS[b.props.kind].row + 0.05);
// The square each character of a Karo's text stands in, as [column, row, character]: a row is filled, then the
// next begins.
export function squares(text: string, cols: number) {
  const out: [number, number, string][] = [];
  let [x, y] = [0, 0];
  for (const ch of text) {
    if (ch === "\n" || x === cols) [x, y] = [0, y + 1];
    if (ch !== "\n") out.push([x++, y, ch]);
  }
  return out;
}
// The height in mm a maths block needs for its exercises.
export function mathsHeight(p: MathsProps) {
  const lines = Math.ceil(p.exercises.length / p.columns);
  const rows = Math.max(0, ...p.exercises.map((e) => e.grid?.rows ?? 0));
  return Math.max(10, Math.round(lines * (p.format === "written" ? (rows + 1) * KARO : p.size * PT * 2.4)));
}
// Where the text on a ruling lies in its block: a line of text to a row, the baseline on the row's writing line.
// The box ends below the last row's descenders, so text past the last row is cut off.
// On Karo the field only takes the typing: its letters are unseen and as wide as a square, so the caret stands
// between the squares, and `Lines` draws the characters.
export function writtenStyle(b: RulingBlock, k: number): CSSProperties {
  const { row, at, base, size } = RULINGS[b.props.kind];
  if (!at)
    return {
      fontFamily: "Geist Mono Variable",
      fontSize: size * k,
      lineHeight: `${row * k}px`,
      // Geist Mono's characters are 0.6 em wide.
      letterSpacing: (row - 0.6 * size) * k,
      top: 0,
      width: colsOf(b) * row * k,
      height: rowsOf(b) * row * k,
      whiteSpace: "break-spaces",
      lineBreak: "anywhere",
      color: "transparent",
      caretColor: "#222222",
    };
  const font = FONTS[b.props.font ?? "andika"];
  const top = base - row / 2 - font[2] * size;
  return {
    fontFamily: font[1],
    fontSize: size * k,
    lineHeight: `${row * k}px`,
    top: top * k,
    height: (rowsOf(b) * row - top + Math.max(0, base + size / 2 - row)) * k,
    color: b.props.trace ? "#aaaaaa" : undefined,
  };
}
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
// How far in mm a text keeps its letters from its box's edge, down and across: its border, and the room a
// PowerPoint text box leaves. A text with neither fill nor border stays where sheets saved before had it.
export function inset(p: TextProps, shape: boolean) {
  const [filled, edged] = [p.fill, p.stroke].map((c) => !!c && c !== "none");
  const edge = edged ? (p.strokeWidth ?? 0.5) : 0;
  return shape || filled || edged ? [1.3 + edge, 2.5 + edge, edge] : [0, 0, 0];
}
// The count before each numbered block. Blocks count in reading order, page after page; the letters start over
// after each number, so tasks can have parts.
export function numbers(doc: Doc) {
  const out = new Map<string, number>();
  const count = { "1": 0, a: 0 };
  for (const page of doc.pages)
    for (const b of [...page.blocks].sort((a, b) => a.y - b.y || a.x - b.x)) {
      if (!counts(b.mark)) continue;
      const kind = b.mark.includes("1") ? "1" : "a";
      if (kind === "1") count.a = 0;
      out.set(b.id, ++count[kind]);
    }
  return out;
}
// The `n`th number or letter of a numbering, in its look.
export function Count({ mark, n }: { mark: string; n: number }) {
  const text = mark.replace("o", "").replace(/[1a]/, (c) => (c === "1" ? String(n) : String.fromCharCode(97 + ((n - 1) % 26))));
  return mark.endsWith("o") ? <span className="ring">{text}</span> : <>{text}</>;
}

// Drawn from the start corner along its own axis; a wide unseen stroke is what a finger grabs. The length stands
// over the middle, turned so it never reads upside down.
function Line({ block, k, solved }: { block: ShapeBlock; k: number; solved: boolean }) {
  const { kind, stroke, strokeWidth, dash, ticks, label } = block.props;
  const [x, y] = [far(block, 1, false) ? block.w : 0, far(block, 0, false) ? block.h : 0];
  const angle = (Math.atan2(block.h - 2 * y, block.w - 2 * x) * 180) / Math.PI;
  const length = Math.hypot(block.w, block.h);
  const head = kind === "arrow" ? 2 + strokeWidth * 3 : 0;
  const dashes = dash === "dashed" ? `${strokeWidth * 4} ${strokeWidth * 3}` : dash === "dotted" ? `0 ${strokeWidth * 2.5}` : undefined;
  return (
    <svg>
      <g transform={`scale(${k}) translate(${x} ${y}) rotate(${angle})`} stroke={stroke} strokeWidth={strokeWidth} fill={stroke}>
        <line x2={length} stroke="transparent" strokeWidth={10} />
        <line x2={length - head} strokeDasharray={dashes} strokeLinecap={dash === "dotted" ? "round" : undefined} />
        {head > 0 && <polygon stroke="none" points={`${length},0 ${length - head},${-head / 2} ${length - head},${head / 2}`} />}
        {ticks && [0, ...(head ? [] : [length])].map((at) => <line key={at} x1={at} x2={at} y1={-1.5} y2={1.5} />)}
        {(label === "show" || (label === "key" && solved)) && (
          <text x={length / 2} y={-2} transform={Math.abs(angle) > 90 ? `rotate(180 ${length / 2} 0)` : undefined} textAnchor="middle" fontFamily="Andika" fontSize={12 * PT} stroke="none" fill={label === "key" ? "#c0392b" : undefined}>
            {(Math.round(length * 10) / 100).toLocaleString("de")} cm
          </text>
        )}
      </g>
    </svg>
  );
}

const UP = { top: "flex-start", middle: "center", bottom: "flex-end" };
// A text or a shape with its text. The editor passes the field the text is typed in.
function Frame({ block, k, children }: { block: TextBlock | ShapeBlock; k: number; children?: ReactNode }) {
  const p = boxed(block)!;
  const [down, across, edge] = inset(p, block.type === "shape");
  return (
    <div
      className="frame"
      style={{
        ...textStyle(p, k),
        background: p.fill,
        border: edge ? `${edge * k}px ${p.dash ?? "solid"} ${p.stroke}` : undefined,
        borderRadius: p.kind === "circle" ? "50%" : p.kind === "rounded" ? 4 * k : 0,
        padding: `${(down - edge) * k}px ${(across - edge) * k}px`,
        justifyContent: UP[p.valign ?? "top"],
      }}
    >
      {children ?? <p>{p.text}</p>}
    </div>
  );
}

// Drawn in mm: the SVG's own scale takes it to the block's size. The editor passes the field the text is typed in.
function Lines({ block, k, children }: { block: RulingBlock; k: number; children?: ReactNode }) {
  const { row, at, band, size } = RULINGS[block.props.kind];
  const { text = "", trace } = block.props;
  const rows = rowsOf(block);
  const cols = colsOf(block);
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
        {!at && cols > 0 && squares(text, cols).map(([x, y, ch], i) => y < rows && (
          <text key={-i - 1} x={(x + 0.5) * row} y={(y + 0.5) * row} fontFamily="Andika" fontSize={size} textAnchor="middle" dominantBaseline="central" stroke="none" fill={trace ? "#aaaaaa" : "currentColor"}>
            {ch}
          </text>
        ))}
      </svg>
      {children ?? (at && text && <p className="written" style={writtenStyle(block, k)}>{text}</p>)}
    </div>
  );
}

// A number of an exercise, or the gap in its place. The answer key fills the gap.
function Part({ e, part, solved }: { e: Exercise; part: "a" | "b" | "result" | "rest"; solved: boolean }) {
  const gap = part === "rest" || part === (e.hide ?? "result");
  return gap ? <u>{solved && e[part]}</u> : <>{e[part]}</>;
}

// A written exercise: squared paper with a character to a square. All of a block's exercises get the same paper.
function Karo({ grid, cols, rows, k, solved }: { grid: Grid; cols: number; rows: number; k: number; solved: boolean }) {
  const each = (n: number) => Array.from({ length: n + 1 }, (_, i) => i);
  return (
    <svg width={cols * KARO * k} height={rows * KARO * k} viewBox={`0 0 ${cols} ${rows}`}>
      <g stroke="#9db4c8" strokeWidth={0.03}>
        {each(cols).map((x) => <line key={x} x1={x} x2={x} y2={rows} />)}
        {each(rows).map((y) => <line key={-y - 1} x2={cols} y1={y} y2={y} />)}
      </g>
      {grid.lines.map(([x1, x2, y, kind], i) => (solved || !kind) && <line key={i} className={kind ? "answer" : ""} x1={x1} x2={x2} y1={y} y2={y} stroke="currentColor" strokeWidth={0.08} />)}
      {grid.cells.map(([x, y, ch, kind], i) => (solved || !kind) && (
        <text key={i} className={kind ? "answer" : ""} x={x + 0.5} y={y + 0.5} fontSize={kind === 2 ? 0.45 : 0.75} textAnchor="middle" dominantBaseline="central" fill="currentColor">
          {ch}
        </text>
      ))}
    </svg>
  );
}

function Maths({ block, k, solved }: { block: MathsBlock; k: number; solved: boolean }) {
  const p = block.props;
  const cols = Math.max(0, ...p.exercises.map((e) => e.grid?.cols ?? 0));
  const rows = Math.max(0, ...p.exercises.map((e) => e.grid?.rows ?? 0));
  const style = { fontSize: p.size * PT * k, gridTemplateColumns: `repeat(${p.columns}, 1fr)`, "--gap": `${String(p.max).length + 1.5}ch` };
  return (
    <div className={`maths ${p.format}${solved ? " solved" : ""}`} style={style as CSSProperties}>
      {p.exercises.map((e, i) => (
        <div key={i}>
          {p.numbering && <b><Count mark={p.numbering} n={i + 1} /></b>}
          {e.grid ? (
            <Karo grid={e.grid} cols={cols} rows={rows} k={k} solved={solved} />
          ) : (
            <span>
              <Part e={e} part="a" solved={solved} /> {SIGNS[e.op]} <Part e={e} part="b" solved={solved} /> = <Part e={e} part="result" solved={solved} />
              {e.rest > 0 && <> R <Part e={e} part="rest" solved={solved} /></>}
            </span>
          )}
        </div>
      ))}
      {!p.exercises.length && <span className="hint">Keine Aufgabe möglich</span>}
    </div>
  );
}

// What a block shows, at `k` pixels per mm. Sizes inside a block are in em of a font size set to the scale.
// `solved` fills in the answers of the maths exercises.
export function Draw({ block, k, solved = false, children }: { block: Block; k: number; solved?: boolean; children?: ReactNode }) {
  if (block.type === "maths") return <Maths block={block} k={k} solved={solved} />;
  if (block.type === "text" || (block.type === "shape" && !isLine(block))) return <Frame block={block} k={k}>{children}</Frame>;
  if (block.type === "shape") return <Line block={block} k={k} solved={solved} />;
  if (block.type === "ruling") return <Lines block={block} k={k}>{children}</Lines>;
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
// number of a counted block; a symbol has none. Beside a text it starts as far down as the text's first line, and
// beside a line its middle is level with the line's start.
export function Mark({ block, k, n }: { block: Block; k: number; n?: number }) {
  if (!block.mark) return null;
  const style = textStyle(boxed(block) ?? { text: "", size: 14, align: "left" }, k);
  return (
    <b className="mark" style={{ ...style, textDecoration: "none", paddingTop: block.type === "text" ? inset(block.props, false)[0] * k : 0, translate: isLine(block) ? "0 -50%" : undefined }}>
      {n ? <Count mark={block.mark} n={n} /> : <img src={symbol(block.mark)} alt="" />}
    </b>
  );
}

// A page with nothing to take hold of, at `k` pixels per mm: page one drawn small in the list, every page at its
// true size in the PDF. The answer key says on each page that it is one.
export function Paper({ doc, k, page = 0, solved = false }: { doc: Doc; k: number; page?: number; solved?: boolean }) {
  const all = read(doc);
  const ns = numbers(all);
  const [w, h] = sizeOf(all, page);
  return (
    <div className={w > h ? "paper wide" : "paper"} style={{ width: w * k, height: h * k }}>
      {all.pages[page].blocks.map((b) => (
        <div key={b.id} className="block" style={{ left: b.x * k, top: b.y * k, width: b.w * k, height: b.h * k, zIndex: b.z }}>
          <Draw block={b} k={k} solved={solved} />
          <Mark block={b} k={k} n={ns.get(b.id)} />
        </div>
      ))}
      {solved && <b className="key" style={{ top: 5 * k, right: 15 * k, fontSize: 11 * PT * k }}>Lösungen</b>}
    </div>
  );
}
