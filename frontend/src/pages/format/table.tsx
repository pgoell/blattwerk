// A table's rows, its pen and the borders that pen draws.
import { useEffect, useState } from "react";
import { Scissors, TextAlignCenter, TextAlignEnd, TextAlignStart, type LucideIcon } from "lucide-react";
import { rectOf, spanAt, widthsOf, type Rect } from "../../cells";
import type { Border } from "../../borders";
import type { LineStyle, Pen } from "../../edges";
import { boxed, fontOf, sum, type Align, type Block, type TableBlock } from "../../sheet";
import type { Picked } from "../Field";
import { FontSelect, unknownFont } from "./font";
import { Gaps } from "./gaps";
import { Num } from "./num";
import { Syllables } from "./syllables";
import { TraceControls } from "./trace";
import { syllabled, worded } from "./words";
import type { Doc } from "../../sheet";

const ALIGNS: [Align, string, LucideIcon][] = [["left", "Links", TextAlignStart], ["center", "Mitte", TextAlignCenter], ["right", "Rechts", TextAlignEnd]];

// The one size that the lines from `from` to `to` share, or undefined where they differ by more than 0.005 mm.
const alike = (sizes: number[], from: number, to: number) => {
  const picked = sizes.slice(from, to + 1);
  return picked.every((s) => Math.abs(s - picked[0]) <= 0.005) ? picked[0] : undefined;
};

// The width and height in mm that the panel shows: the open cell's own, or the picked cells' shared sizes.
function sizeFields(t: TableBlock, cell: number, reach: number | undefined, laid: number[]): { width?: number; height?: number } {
  const [r, c, h, w] = spanAt(t.props, cell);
  const [r0, c0, r1, c1]: Rect = reach === undefined ? [r, c, r + h - 1, c + w - 1] : rectOf(t.props, cell, reach);
  const widths = widthsOf(t.props.cols, t.w);
  const width = reach === undefined ? sum(widths.slice(c0, c1 + 1)) : alike(widths, c0, c1);
  const height = !laid.length ? undefined : reach === undefined ? sum(laid.slice(r0, r1 + 1)) : alike(laid, r0, r1);
  return { width, height };
}

// The border buttons of the panel, each with the border it draws.
const BORDERS: [Border, string][] = [
  ["all", "Alle"],
  ["inner", "Innen"],
  ["outer", "Außen"],
  ["top", "Oben"],
  ["bottom", "Unten"],
  ["left", "Links"],
  ["right", "Rechts"],
  ["across", "Innen waagerecht"],
  ["down", "Innen senkrecht"],
];

export function TablePanel({
  sel, style, part, look, mendWord, doc, words, cell, reach, rank, merge, unmerge, laid, sizeCells, evenCells, lines, cutting, border, traced, gap, every,
}: {
  sel: Block[];
  style: (type: Block["type"], props: object, key?: string, only?: string[]) => void;
  part?: Picked;
  look: (props: object, key?: string) => void;
  mendWord: (keys: string[], counts: number[] | undefined, id: string) => void;
  doc: Doc;
  words: string[];
  cell?: number;
  reach?: number;
  rank: (b: TableBlock, axis: "row" | "col", i: number, add: boolean, after?: boolean) => void;
  merge: () => void;
  unmerge: () => void;
  laid: number[];
  sizeCells: (axis: "col" | "row", mm: number) => void;
  evenCells: (axis: "col" | "row") => void;
  lines: (patch: { style?: LineStyle; width?: number }, key?: string) => void;
  cutting: (on: boolean) => void;
  border?: (which: Border, pen: Pen) => void;
  traced: (props: object) => void;
  gap: (on: boolean) => void;
  every: (n: number) => void;
}) {
  const [pen, setPen] = useState<Pen>({ style: "solid", width: 0.25 });
  const tables = sel.filter((b): b is TableBlock => b.type === "table");
  const fixed = sel.some((b) => b.locked);
  const text = sel.map(boxed).find((p) => p);
  // The pen starts at the first table's lines each time a cell opens.
  const open = cell !== undefined;
  useEffect(() => {
    if (tables[0]) setPen({ style: tables[0].props.lineStyle ?? "solid", width: tables[0].props.lineWidth ?? 0.25 });
  }, [open]);
  // What the line controls show: the table's own lines with no cell open, else the pen.
  const lineShown: Pen = !open && tables[0] ? { style: tables[0].props.lineStyle ?? "solid", width: tables[0].props.lineWidth ?? 0.25 } : pen;
  // The border buttons draw on the open cell's rect (or the cells picked with it), or on the whole table with no cell open.
  // A rect of one cell or of one merged cell has no inner line, and one row or one column has no line across or down.
  const grid = tables[0]?.props;
  let rect: Rect = [0, 0, 0, 0];
  if (grid && cell === undefined) rect = [0, 0, grid.cells.length - 1, grid.cols.length - 1];
  else if (grid && cell !== undefined) {
    if (reach === undefined) {
      const [r, c, h, w] = spanAt(grid, cell);
      rect = [r, c, r + h - 1, c + w - 1];
    } else rect = rectOf(grid, cell, reach);
  }
  const [r0, c0, r1, c1] = rect;
  const first = grid ? spanAt(grid, r0 * grid.cols.length + c0) : undefined;
  const single = !!first && first[0] === r0 && first[1] === c0 && first[2] === r1 - r0 + 1 && first[3] === c1 - c0 + 1;
  const off = (which: Border) => (which === "across" ? single || r0 === r1 : which === "down" ? single || c0 === c1 : which === "inner" && (single || r0 === r1 || c0 === c1));
  if (!tables.length) return null;
  return (
    <>
          <h2>Tabelle</h2>
          {/* More or fewer rows and columns, for one table: each has cells of its own. They come and go at the end,
              or beside the cell being edited, as in PowerPoint. */}
          {tables.length === 1 &&
            (["Zeile", "Spalte"] as const).map((name, i) => {
              const axis = i ? "col" : "row";
              const n = [tables[0].props.cells.length, tables[0].props.cols.length];
              if (cell === undefined)
                return (
                  <div key={name} className="seg">
                    <button aria-label={`Eine ${name} weniger`} disabled={fixed} onClick={() => rank(tables[0], axis, n[i] - 1, false)}>−</button>
                    <output>{n[i] === 1 ? `1 ${name}` : `${n[i]} ${name}n`}</output>
                    <button aria-label={`Eine ${name} mehr`} disabled={fixed} onClick={() => rank(tables[0], axis, n[i], true)}>＋</button>
                  </div>
                );
              const [r, c, h, w] = spanAt(tables[0].props, cell);
              const at = i ? c : r;
              const after = i ? c + w : r + h;
              return (
                <div key={name} className="acts">
                  <button onClick={() => rank(tables[0], axis, at, true)}>{name} {i ? "links" : "darüber"}</button>
                  <button onClick={() => rank(tables[0], axis, after, true, true)}>{name} {i ? "rechts" : "darunter"}</button>
                </div>
              );
            })}
          {/* The last row or column stays. A disabled button would take the focus from the cell. */}
          {tables.length === 1 && cell !== undefined && (
            <div className="acts">
              <button aria-disabled={tables[0].props.cells.length < 2} onClick={() => rank(tables[0], "row", spanAt(tables[0].props, cell)[0], false)}>Zeile löschen</button>
              <button aria-disabled={tables[0].props.cols.length < 2} onClick={() => rank(tables[0], "col", spanAt(tables[0].props, cell)[1], false)}>Spalte löschen</button>
            </div>
          )}
          {tables.length === 1 && cell !== undefined && (
            <div className="acts">
              <button aria-disabled={reach === undefined} onClick={() => reach !== undefined && merge()}>Zellen verbinden</button>
              <button aria-disabled={!(spanAt(tables[0].props, cell)[2] * spanAt(tables[0].props, cell)[3] > 1)} onClick={() => spanAt(tables[0].props, cell)[2] * spanAt(tables[0].props, cell)[3] > 1 && unmerge()}>Zellen teilen</button>
            </div>
          )}
          {tables.length === 1 && cell !== undefined && (
            <>
              <Num label="Spaltenbreite" value={sizeFields(tables[0], cell, reach, laid).width} disabled={fixed} onCommit={(n) => n > 0 && sizeCells("col", n)} />
              <Num label="Zeilenhöhe" value={sizeFields(tables[0], cell, reach, laid).height} disabled={fixed} onCommit={(n) => n > 0 && sizeCells("row", n)} />
              <div className="acts">
                <button disabled={fixed} onClick={() => evenCells("col")}>Spalten gleichmäßig verteilen</button>
                <button disabled={fixed} onClick={() => evenCells("row")}>Zeilen gleichmäßig verteilen</button>
              </div>
            </>
          )}
          <FontSelect label="Schriftart der Tabelle" value={fontOf(tables[0].props.font)} unknown={unknownFont(tables.map((b) => b.props.font))} onChange={(font) => style("table", { font })} />
          <div className="seg">
            <button aria-label="Schrift kleiner" onClick={() => style("table", { size: Math.max(8, tables[0].props.size - 2) })}>−</button>
            <output>{tables[0].props.size} pt</output>
            <button aria-label="Schrift größer" onClick={() => style("table", { size: tables[0].props.size + 2 })}>＋</button>
          </div>
          <div className="seg">
            {ALIGNS.map(([value, label, Icon]) => (
              <button key={value} className={tables[0].props.align === value ? "on" : ""} aria-label={label} title={label} aria-pressed={tables[0].props.align === value} onClick={() => style("table", { align: value })}>
                <Icon size={14} aria-hidden />
              </button>
            ))}
          </div>
          <label>
            Farbe
            <input type="color" value={tables[0].props.color ?? "#222222"} onChange={(e) => style("table", { color: e.target.value }, "color")} />
          </label>
          <label>
            Linien
            <input type="color" value={tables[0].props.line} onChange={(e) => style("table", { line: e.target.value }, "line")} />
          </label>
          <label>
            Linienart
            <select
              aria-label="Linienart"
              value={lineShown.style}
              onChange={(e) => (open ? setPen({ ...pen, style: e.target.value as LineStyle }) : lines({ style: e.target.value as LineStyle }))}
            >
              <option value="solid">Durchgezogen</option>
              <option value="dashed">Gestrichelt</option>
              <option value="dotted">Gepunktet</option>
              <option value="none">Keine</option>
            </select>
          </label>
          <label>
            Linienstärke
            <input
              type="range"
              min={0.25}
              max={3}
              step={0.25}
              value={lineShown.width}
              onChange={(e) => (open ? setPen({ ...pen, width: +e.target.value }) : lines({ width: +e.target.value }, "lineWidth"))}
            />
          </label>
          <output>{lineShown.width.toFixed(2).replace(".", ",")} mm</output>
          {border && (
            <div role="group" aria-label="Rahmen" className="borders">
              {BORDERS.map(([which, label]) => (
                <button key={which} aria-disabled={off(which)} onClick={() => !off(which) && border(which, lineShown)}>
                  {label}
                </button>
              ))}
            </div>
          )}
          <button className={tables[0].props.cut ? "wide on" : "wide"} aria-pressed={!!tables[0].props.cut} onClick={() => cutting(!tables[0].props.cut)}>
            <Scissors size={14} aria-hidden />
            Schneidelinien
          </button>
          <button className={tables[0].props.head ? "on" : ""} aria-pressed={!!tables[0].props.head} onClick={() => style("table", { head: !tables[0].props.head })}>
            Kopfzeile
          </button>
          <TraceControls props={tables[0].props} font={tables[0].props.font} onChange={traced} />
          {!text && <Syllables key={sel.find(syllabled)?.id} sel={sel} part={part} look={look} style={style} mendWord={mendWord} doc={doc} words={words} />}
          {!text && <Gaps key={`gaps-${sel.find(worded)?.id}`} sel={sel} part={part} cell={cell} look={look} style={style} gap={gap} every={every} />}
          <p className="hint">Doppelklick auf eine Zelle, um hineinzuschreiben.</p>
    </>
  );
}
