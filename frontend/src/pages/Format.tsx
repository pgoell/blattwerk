// The format panel's settings for the school blocks, and the numbering any block can have.
import { useEffect, useRef, useState } from "react";
import { AlignVerticalJustifyCenter, AlignVerticalJustifyEnd, AlignVerticalJustifyStart, FlipHorizontal2, FlipVertical2, List as Bullets, ListOrdered, Lock, LockOpen, RotateCcw, RotateCw, TextAlignCenter, TextAlignEnd, TextAlignStart, type LucideIcon } from "lucide-react";
import Numbering from "../components/Numbering";
import { FONTS, MARGIN, RULINGS, boxed, counts, dir, isLine, mathsHeight, parasOf, rowsOf, symbol, tall, type Align, type Axis, type Block, type Box, type Corner, type List, type MathsProps, type Ruling, type RulingBlock, type TableBlock, type Valign } from "../sheet";
import type { Marks, Picked } from "./Field";
import Maths from "./Maths";
import { SYMBOLS } from "../symbols";

type Props = {
  sel: Block[];
  // Sets props on every selected block of one type.
  style: (type: Block["type"], props: object, key?: string) => void;
  // Sets what a text and a shape share on every selected one of them.
  look: (props: object, key?: string) => void;
  // Sets bold, italic, underline or colour on the words picked in the text being edited, or else as `look` does.
  paint: (props: Marks, key?: string) => void;
  // Makes a list of the paragraphs the caret stands in, or else of all the selected texts.
  itemize: (kind: List) => void;
  // What is picked in the text being edited.
  part?: Picked;
  place: (boxes: [string, Partial<Box>][], key?: string) => void;
  // Adds a row or a column to a table before the one at `i`, or takes the one at `i` away.
  rank: (b: TableBlock, axis: "row" | "col", i: number, add: boolean) => void;
  // The cell of the table being edited, counted row by row.
  cell?: number;
  // Starts or ends crop mode; absent unless one picture that is not locked is selected.
  crop?: () => void;
  cropping: boolean;
  // Turns what is selected by so many degrees: a group picked whole as one, a loose block about its own centre.
  spin: (by: number) => void;
  // Mirrors what is selected across or down: a group picked whole as one, a loose block in itself.
  mirror: (axis: Axis) => void;
  // Whether the block is a thing by itself: loose, or picked out of its group.
  alone: (b: Block) => boolean;
  // Whether a new width sets the height to match, in the fields and on the handles.
  lock: boolean;
  setLock: (on: boolean) => void;
  // The width and height in mm of the page in use.
  size: number[];
};

const ALIGNS: [Align, string, LucideIcon][] = [["left", "Links", TextAlignStart], ["center", "Mitte", TextAlignCenter], ["right", "Rechts", TextAlignEnd]];
const LISTS: [List, string, LucideIcon][] = [["bullet", "Aufzählung", Bullets], ["number", "Nummerierung", ListOrdered]];
const VALIGNS: [Valign, string, LucideIcon][] = [["top", "Oben", AlignVerticalJustifyStart], ["middle", "Mitte", AlignVerticalJustifyCenter], ["bottom", "Unten", AlignVerticalJustifyEnd]];
// The turns by a quarter and the two flips: a flip has no degrees.
const TURNS: [string, LucideIcon, number][] = [["Rechtsdrehung 90°", RotateCw, 90], ["Linksdrehung 90°", RotateCcw, -90], ["Horizontal spiegeln", FlipHorizontal2, 0], ["Vertikal spiegeln", FlipVertical2, 0]];
const round = (n: number) => Math.round(n * 100) / 100;
// An angle as a block stores it: from 0 up to 360.
export const norm = (a: number) => round(((a % 360) + 360) % 360) % 360;
// The box around several blocks.
export const bounds = (bs: Box[]) => {
  const [x, y] = [Math.min(...bs.map((b) => b.x)), Math.min(...bs.map((b) => b.y))];
  return { x, y, w: Math.max(...bs.map((b) => b.x + b.w)) - x, h: Math.max(...bs.map((b) => b.y + b.h)) - y };
};
// The level box around a turned block's outline. It has the block's centre.
export const outline = <T extends Box>(b: T): T => {
  const [c, s] = dir(b).map(Math.abs);
  const [w, h] = [b.w * c + b.h * s, b.w * s + b.h * c];
  return { ...b, x: b.x + (b.w - w) / 2, y: b.y + (b.h - h) / 2, w, h };
};
// The corner a line starts at after a quarter turn clockwise.
const NEXT: Record<Corner, Corner> = { nw: "ne", ne: "se", se: "sw", sw: "nw" };
// A block on its side whose width and height differ by an odd count of hundredths has its outline half a
// hundredth off the sheet's hundredths. This is how far its stored place lies from the one it is meant to have,
// to the right and up: so four quarter turns lead back to the hundredth.
const lean = (b: Box) => ((b.angle ?? 0) % 180 === 90 && Math.round((b.w + b.h) * 100) % 2 ? Math.sign(b.w - b.h) * 0.005 : 0);
// The box around the blocks as they are meant to lie, turned or not: the frame a group shows.
const hull = (bs: Box[]) => bounds(bs.map((b) => outline({ ...b, x: b.x - lean(b), y: b.y + lean(b) })));
// A quarter turn clockwise of the blocks as one. The box around them goes on its side about its middle, to the
// hundredth: half a hundredth too many goes away one time and comes back the next. In it each block's centre goes
// round and keeps its distances to the edges, so all stays on the hundredths. A line has no angle: its box goes on
// its side, and the line starts at the next corner.
const quarter = (bs: Block[]): Block[] => {
  const all = hull(bs);
  const d =Math.trunc(Math.round((all.w - all.h) * 100) / 2) / 100;
  return bs.map((b) => {
    const to = isLine(b) ? { ...b, w: b.h, h: b.w, props: { ...b.props, from: NEXT[b.props.from ?? "nw"] } } : { ...b, angle: norm((b.angle ?? 0) + 90) };
    // As far from the left as the centre was from the bottom, and as far from the top as it was from the left.
    const x = all.x + d + (all.y + all.h - (b.y + lean(b) + b.h / 2));
    const y = all.y - d + (b.x - lean(b) + b.w / 2 - all.x);
    return { ...to, x: round(x - to.w / 2 + lean(to)), y: round(y - to.h / 2 - lean(to)) };
  });
};
// The blocks turned as one by `by` degrees about the middle of the box around them, as the handle turns a
// selection and PowerPoint a group: each block's centre goes round, and its angle goes on. One block turns on its
// spot. Quarters are exact, and a line goes by them only.
export const swung = (bs: Block[], by: number): Block[] => {
  if (by % 90 === 0) return Array.from({ length: (((by / 90) % 4) + 4) % 4 }).reduce<Block[]>(quarter, bs);
  const all = hull(bs);
  const [cx, cy] = [all.x + all.w / 2, all.y + all.h / 2];
  const [c, s] = dir({ angle: by });
  return bs.map((b) => {
    const [x, y] = [b.x + b.w / 2 - cx, b.y + b.h / 2 - cy];
    return { ...b, x: round(cx + x * c - y * s - b.w / 2), y: round(cy + x * s + y * c - b.h / 2), angle: norm((b.angle ?? 0) + by) };
  });
};
// The blocks mirrored as one, across for `x` and down for `y`, about the middle of the box around them: each goes
// to the other side, and the box stays. A picture, a symbol, a shape and a text in an outline are mirrored in
// themselves too, as the page shows them, and their angle with them. A line's start changes corners instead. A
// shape's text stays readable, and so does all else: in a group it moves and leans the other way, alone it stays.
export const mirrored = (bs: Block[], axis: Axis): Block[] => {
  const swap: Record<Corner, Corner> = axis === "x" ? { nw: "ne", ne: "nw", sw: "se", se: "sw" } : { nw: "sw", sw: "nw", ne: "se", se: "ne" };
  const [flag, size] = axis === "x" ? (["flipX", "w"] as const) : (["flipY", "h"] as const);
  const all = hull(bs);
  return bs.map((b) => {
    const own = b.type === "image" || b.type === "symbol" || b.type === "shape" || drawn(b);
    if (!own && bs.length === 1) return b;
    // As far from the far edge as it was from the near one. A block on its side leans the same way after.
    const at = { [axis]: round(2 * all[axis] + all[size] - b[axis] - b[size] + (axis === "x" ? 2 : -2) * lean(b)) };
    // `isLine` tells the compiler that every shape it turns down is no shape, so the type is read first.
    // An outline mirrors as a picture does; a box looks the same either way.
    const flips = own && (b.type !== "shape" || drawn(b));
    if (isLine(b)) return { ...b, ...at, props: { ...b.props, from: swap[b.props.from ?? "nw"] } };
    // A level block names no angle, and stays so.
    return { ...b, ...at, ...(b.angle && { angle: norm(-b.angle) }), ...(flips && { [flag]: !b[flag] }) };
  });
};

// Whether the words picked in the field have a look, or with no field every selected text: as in PowerPoint, a
// look goes on unless all have it. A text has it when all its words do, of their own or through the block; one
// with no words has what the block has.
export const has = (sel: Block[], part: Picked | undefined, name: "bold" | "italic" | "underline") =>
  part
    ? !!part.marks[name]
    : sel.every((b) => {
        const text = boxed(b);
        if (!text) return true;
        const runs = parasOf(text).flatMap((p) => p.runs);
        return runs.length ? runs.every((r) => r[name] ?? text[name]) : !!text[name];
      });

// Whether a text or a shape has a frame drawn as an outline, which a flip mirrors.
export const drawn = (b: Block) => (b.type === "shape" || b.type === "text") && ["triangle", "star", "bubble"].includes(b.props.kind ?? "rect");

export default function Format({ sel, style, look, paint, itemize, part, place, rank, cell, crop, cropping, spin, mirror, alone, lock, setLock, size: [W, H] }: Props) {
  // A locked block neither turns nor flips. A table stays level, a line turns by its ends, and only a picture, a
  // symbol, a shape or a text in an outline can flip. A group picked whole goes as one: a line in it goes round
  // with it by quarters, and whatever is in it changes sides in a flip.
  const fixed = sel.some((b) => b.locked);
  const level = fixed || sel.some((b) => b.type === "table" || (isLine(b) && alone(b)));
  const plain = fixed || !sel.some((b) => !alone(b) || b.type === "image" || b.type === "symbol" || b.type === "shape" || drawn(b));
  const of = <T extends Block["type"]>(type: T) => sel.filter((b): b is Extract<Block, { type: T }> => b.type === type);
  // The first block of a type shows its settings; a change goes to all of them.
  // A shape that is no line holds text as a text block does.
  const text = sel.map(boxed).find((p) => p);
  // Picked words show their own look, and the list is that of the caret's paragraph, or of the text's first.
  const shown = { ...text, ...part?.marks };
  const kind = text && (part ?? parasOf(text)[0]).list;
  const rulings = of("ruling");
  const tables = of("table");
  const [points] = of("points");
  const [sign] = of("symbol");
  // The generator's limits belong to one block.
  const maths = sel.length === 1 && sel[0].type === "maths" ? sel[0] : undefined;
  const { mark } = sel[0];

  // A ruling keeps its rows when its type changes, so the block's height follows.
  const rule = (kind: Ruling, rows?: number) => {
    style("ruling", { kind }, "ruling");
    place(rulings.map((b) => [b.id, tall(b, round(Math.max(1, rows ?? rowsOf(b)) * RULINGS[kind].row))]), "ruling");
  };
  // How far a point can go until it meets a margin, moving `by` each step. No limit where it does not move.
  const room = (at: number, by: number, max: number) => (Math.abs(by) < 1e-9 ? Infinity : ((by > 0 ? max - MARGIN : MARGIN) - at) / by);
  // A ruling grows down its own axis, which a turn points anywhere on the page, until a corner of its far edge
  // would cross the margin it grows towards. Whole rows, and one at least.
  const fill = (b: RulingBlock) => {
    const [c, s] = dir(b);
    // The corner the block starts at; the other end of that edge lies its width along.
    const [x, y] = [b.x + (b.w - b.w * c + b.h * s) / 2, b.y + (b.h - b.w * s - b.h * c) / 2];
    const most = Math.min(room(x, -s, W), room(x + b.w * c, -s, W), room(y, c, H), room(y + b.w * s, c, H));
    return tall(b, round(Math.max(1, Math.floor(most / RULINGS[b.props.kind].row + 0.05)) * RULINGS[b.props.kind].row));
  };
  // A ruling fills the room between the margins along the way it lies: both ends go out from its centre until a
  // corner would cross a margin. A slanted one stays as it is when it lies past a margin along its way and has
  // less room there than it is high.
  const wide = (b: RulingBlock): Partial<Box> => {
    const [c, s] = dir(b);
    // The middle of each long edge.
    const mids = [-1, 1].map((side) => [b.x + (b.w - side * b.h * s) / 2, b.y + (b.h + side * b.h * c) / 2]);
    const [back, on] = [-1, 1].map((way) => Math.min(...mids.flatMap(([x, y]) => [room(x, way * c, W), room(y, way * s, H)])));
    // Rounded down, so that no corner crosses.
    const w = Math.floor((back + on) * 100 + 1e-6) / 100;
    // A slanted one that fills the room to a hair stays too: its place is rounded, so a second press would find
    // a little room again, and the more of it the closer the block lies to level or upright. So its place is
    // rounded finer, to keep that hair thin.
    const hair = 0.02 + 0.0001 / Math.min(Math.abs(c), Math.abs(s));
    const slanted = Math.abs(c * s) > 1e-9;
    const fine = (n: number) => (slanted ? Math.round(n * 1e4) / 1e4 : round(n));
    if (!(w > 0 && w < Infinity) || (slanted && (((back < 0 || on < 0) && w < b.h) || [back, on].every((end) => Math.abs(end - b.w / 2) < hair)))) return {};
    // A level block keeps its y as it is.
    return { w, x: fine(b.x + (b.w - w + (on - back) * c) / 2), ...(Math.abs(s) > 1e-9 && { y: fine(b.y + ((on - back) * s) / 2) }) };
  };
  // A maths block's height follows its exercises when they need more or less room than before.
  const calc = (props: MathsProps) => {
    style("maths", props, "maths");
    if (mathsHeight(props) !== mathsHeight(maths!.props)) place([[maths!.id, tall(maths!, mathsHeight(props))]], "maths");
  };
  const number = (to?: string) => place(sel.map((b) => [b.id, { mark: to }]));

  // The fields for place, size and angle, as in PowerPoint's size pane. A field shows what all the blocks share.
  // A selection with a group in it is one thing: it shows the box around it, which only moves.
  const whole = sel.some((b) => b.group);
  const box = bounds(sel);
  const shared = (of: (b: Block) => number) => (whole ? undefined : sel.every((b) => of(b) === of(sel[0])) ? of(sel[0]) : undefined);
  // A picture and a symbol always keep their shape.
  const shaped = sel.some((b) => b.type === "image" || b.type === "symbol");
  const keep = lock || shaped;
  const move = (axis: Axis, to: number) => place(sel.map((b) => [b.id, { [axis]: whole ? round(b[axis] + to - box[axis]) : to }]));
  // The corner stays. With the lock each block keeps its own shape.
  const resize = (side: "w" | "h", to: number) => {
    const other = side === "w" ? "h" : "w";
    if (to > 0) place(sel.map((b) => [b.id, { [side]: to, ...(keep && b[side] > 0 && { [other]: round((b[other] * to) / b[side]) }) }]));
  };
  const angle = shared((b) => b.angle ?? 0);
  const turn = (to: number) => norm(to) !== angle && place(sel.map((b) => [b.id, { angle: norm(to) }]));

  return (
    <>
      <div className="geo">
        <h2>Position und Größe in mm</h2>
        <Num label="X" value={whole ? round(box.x) : shared((b) => b.x)} disabled={fixed} onCommit={(n) => move("x", n)} />
        <Num label="Y" value={whole ? round(box.y) : shared((b) => b.y)} disabled={fixed} onCommit={(n) => move("y", n)} />
        <Num label="Breite" value={whole ? round(box.w) : shared((b) => b.w)} disabled={fixed || whole || sel.some(isLine)} onCommit={(n) => resize("w", n)} />
        <Num label="Höhe" value={whole ? round(box.h) : shared((b) => b.h)} disabled={fixed || whole || sel.some(isLine)} onCommit={(n) => resize("h", n)} />
        <Num label="Drehung" value={angle} disabled={level || whole} onCommit={turn} />
        <span>
          °
          <button className={keep ? "ib on" : "ib"} aria-label="Seitenverhältnis sperren" title="Seitenverhältnis sperren" aria-pressed={keep} disabled={fixed || whole || shaped} onClick={() => setLock(!lock)}>
            {keep ? <Lock size={14} aria-hidden /> : <LockOpen size={14} aria-hidden />}
          </button>
        </span>
      </div>
      {text && (
        <>
          <h2>Schrift</h2>
          <select aria-label="Schriftart" value={text.font ?? "andika"} onChange={(e) => look({ font: e.target.value })}>
            {Object.entries(FONTS).map(([font, [name]]) => (
              <option key={font} value={font}>
                {name}
              </option>
            ))}
          </select>
          <div className="seg">
            <button aria-label="Schrift kleiner" onClick={() => look({ size: Math.max(8, text.size - 2) })}>−</button>
            <output>{text.size} pt</output>
            <button aria-label="Schrift größer" onClick={() => look({ size: text.size + 2 })}>＋</button>
          </div>
          <div className="seg">
            {([["bold", "Fett"], ["italic", "Kursiv"], ["underline", "Unterstrichen"]] as const).map(([prop, label]) => (
              <button key={prop} className={`${prop}${has(sel, part, prop) ? " on" : ""}`} aria-label={label} aria-pressed={has(sel, part, prop)} onClick={() => paint({ [prop]: !has(sel, part, prop) })}>
                {label[0]}
              </button>
            ))}
          </div>
          <div className="seg">
            {LISTS.map(([value, label, Icon]) => (
              <button key={value} className={kind === value ? "on" : ""} aria-label={label} title={label} aria-pressed={kind === value} onClick={() => itemize(value)}>
                <Icon size={14} aria-hidden />
              </button>
            ))}
          </div>
          <div className="seg">
            {ALIGNS.map(([value, label, Icon]) => (
              <button key={value} className={text.align === value ? "on" : ""} aria-label={label} title={label} aria-pressed={text.align === value} onClick={() => look({ align: value })}>
                <Icon size={14} aria-hidden />
              </button>
            ))}
          </div>
          <div className="seg">
            {VALIGNS.map(([value, label, Icon]) => (
              <button key={value} className={(text.valign ?? "top") === value ? "on" : ""} aria-label={label} title={label} aria-pressed={(text.valign ?? "top") === value} onClick={() => look({ valign: value })}>
                <Icon size={14} aria-hidden />
              </button>
            ))}
          </div>
          <label>
            Farbe
            <input type="color" value={shown.color ?? "#222222"} onChange={(e) => paint({ color: e.target.value }, "color")} />
          </label>
          <label>
            Zeilenabstand
            <input type="range" min={1} max={3} step={0.1} value={text.spacing ?? 1.3} onChange={(e) => look({ spacing: +e.target.value }, "spacing")} />
          </label>
        </>
      )}
      {rulings.length > 0 && (
        <>
          <h2>Lineatur</h2>
          <select aria-label="Art der Lineatur" value={rulings[0].props.kind} onChange={(e) => rule(e.target.value as Ruling)}>
            {Object.entries(RULINGS).map(([kind, { name }]) => (
              <option key={kind} value={kind}>
                {name}
              </option>
            ))}
          </select>
          <div className="seg">
            <button aria-label="Eine Zeile weniger" disabled={fixed} onClick={() => rule(rulings[0].props.kind, rowsOf(rulings[0]) - 1)}>−</button>
            <output>{rowsOf(rulings[0])} Zeilen</output>
            <button aria-label="Eine Zeile mehr" disabled={fixed} onClick={() => rule(rulings[0].props.kind, rowsOf(rulings[0]) + 1)}>＋</button>
          </div>
          <label>
            Farbe
            <input type="color" value={rulings[0].props.color} onChange={(e) => style("ruling", { color: e.target.value }, "color")} />
          </label>
          <div className="row">
            <button disabled={fixed} onClick={() => place(rulings.map((b) => [b.id, wide(b)]))}>Seitenbreite</button>
            <button disabled={fixed} onClick={() => place(rulings.map((b) => [b.id, fill(b)]))}>Bis Seitenende</button>
          </div>
          <p className="hint">Doppelklick auf die Lineatur, um hineinzuschreiben.</p>
          {RULINGS[rulings[0].props.kind].at && (
            <select aria-label="Schriftart auf den Zeilen" value={rulings[0].props.font ?? "andika"} onChange={(e) => style("ruling", { font: e.target.value })}>
              {Object.entries(FONTS).map(([font, [name]]) => (
                <option key={font} value={font}>
                  {name}
                </option>
              ))}
            </select>
          )}
          <button className={rulings[0].props.trace ? "on" : ""} aria-pressed={!!rulings[0].props.trace} onClick={() => style("ruling", { trace: !rulings[0].props.trace })}>
            Nachspurtext
          </button>
        </>
      )}
      {tables.length > 0 && (
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
                    <output>{n[i]} {name}n</output>
                    <button aria-label={`Eine ${name} mehr`} disabled={fixed} onClick={() => rank(tables[0], axis, n[i], true)}>＋</button>
                  </div>
                );
              const at = i ? cell % n[1] : Math.floor(cell / n[1]);
              return (
                <div key={name} className="acts">
                  <button onClick={() => rank(tables[0], axis, at, true)}>{name} {i ? "links" : "darüber"}</button>
                  <button onClick={() => rank(tables[0], axis, at + 1, true)}>{name} {i ? "rechts" : "darunter"}</button>
                </div>
              );
            })}
          {/* The last row or column stays. A disabled button would take the focus from the cell. */}
          {tables.length === 1 && cell !== undefined && (
            <div className="acts">
              <button aria-disabled={tables[0].props.cells.length < 2} onClick={() => rank(tables[0], "row", Math.floor(cell / tables[0].props.cols.length), false)}>Zeile löschen</button>
              <button aria-disabled={tables[0].props.cols.length < 2} onClick={() => rank(tables[0], "col", cell % tables[0].props.cols.length, false)}>Spalte löschen</button>
            </div>
          )}
          <select aria-label="Schriftart der Tabelle" value={tables[0].props.font ?? "andika"} onChange={(e) => style("table", { font: e.target.value })}>
            {Object.entries(FONTS).map(([font, [name]]) => (
              <option key={font} value={font}>
                {name}
              </option>
            ))}
          </select>
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
          <button className={tables[0].props.head ? "on" : ""} aria-pressed={!!tables[0].props.head} onClick={() => style("table", { head: !tables[0].props.head })}>
            Kopfzeile
          </button>
          <p className="hint">Doppelklick auf eine Zelle, um hineinzuschreiben.</p>
        </>
      )}
      {maths && <Maths key={maths.id} block={maths} apply={calc} />}
      {points && (
        <>
          <h2>Punkte</h2>
          <div className="seg">
            <button aria-label="Ein Punkt weniger" onClick={() => style("points", { max: Math.max(1, points.props.max - 1) })}>−</button>
            <output>{points.props.max}</output>
            <button aria-label="Ein Punkt mehr" onClick={() => style("points", { max: points.props.max + 1 })}>＋</button>
          </div>
        </>
      )}
      {sign && (
        <>
          <h2>Symbol</h2>
          <Symbols value={sign.props.code} onPick={(code) => style("symbol", { code })} />
        </>
      )}
      {crop && (
        <>
          <h2>Bild</h2>
          <button className={cropping ? "wide on" : "wide"} aria-pressed={cropping} onClick={crop}>
            {cropping ? "Fertig" : "Zuschneiden"}
          </button>
        </>
      )}
      <h2>Drehen</h2>
      <div className="seg">
        {TURNS.map(([label, Icon, by]) => (
          <button key={label} aria-label={label} title={label} disabled={by ? level : plain} onClick={() => (by ? spin(by) : mirror(label[0] === "H" ? "x" : "y"))}>
            <Icon size={14} aria-hidden />
          </button>
        ))}
      </div>
      <h2>Nummerierung</h2>
      <Numbering value={mark} onChange={number} symbol={() => number("2B50")} />
      {mark && !counts(mark) && <Symbols value={mark} onPick={number} />}
    </>
  );
}

// A field for a number. What is typed counts on Enter or when the field is left, and Escape drops it. An arrow up
// or down steps by one. `value` is absent where the selected blocks differ.
function Num({ label, value, disabled, onCommit }: { label: string; value?: number; disabled: boolean; onCommit: (n: number) => void }) {
  const [draft, setDraft] = useState<string>();
  // Whether the mouse that is down brought the focus.
  const fresh = useRef(false);
  // The field follows the sheet: a drag or an undo takes the place of what was typed.
  useEffect(() => setDraft(undefined), [value]);
  // Only digits with a comma or a point count: "1e3" and "Infinity" are numbers to JavaScript alone.
  const read = () => (/^-?\d+([.,]\d+)?$/.test(draft?.trim() ?? "") ? round(Number(draft!.replace(",", "."))) : NaN);
  // Without a draft the blur that follows Enter finds nothing to set.
  const commit = (n: number) => {
    setDraft(undefined);
    if (!Number.isNaN(n) && n !== value) onCommit(n);
  };
  return (
    <label>
      {label}
      <input
        className="mm"
        type="text"
        inputMode="decimal"
        disabled={disabled}
        value={draft ?? (value === undefined ? "" : String(round(value)).replace(".", ","))}
        onChange={(e) => setDraft(e.target.value)}
        onFocus={(e) => e.target.select()}
        // Safari puts the caret where the mouse comes up and so drops what the focus selected.
        onMouseDown={(e) => (fresh.current = document.activeElement !== e.target)}
        onMouseUp={(e) => {
          if (fresh.current) e.preventDefault();
          fresh.current = false;
        }}
        onBlur={() => draft !== undefined && commit(read())}
        onKeyDown={(e) => {
          if (e.key === "Enter") commit(read());
          if (e.key === "Escape") setDraft(undefined);
          if (e.key !== "ArrowUp" && e.key !== "ArrowDown") return;
          e.preventDefault();
          commit(round((draft === undefined ? (value ?? NaN) : read()) + (e.key === "ArrowUp" ? 1 : -1)));
        }}
      />
    </label>
  );
}

// Every symbol as a button, narrowed by a search through the German and English names.
function Symbols({ value, onPick }: { value: string; onPick: (code: string) => void }) {
  const [query, setQuery] = useState("");
  const found = SYMBOLS.filter(([, de, en]) => `${de} ${en}`.toLowerCase().includes(query.trim().toLowerCase()));
  return (
    <>
      <input type="text" aria-label="Symbol suchen" placeholder="Suchen, z. B. Schere" value={query} onChange={(e) => setQuery(e.target.value)} />
      <div className="symbols">
        {found.map(([code, de]) => (
          <button key={code} className={code === value ? "on" : ""} aria-label={de} title={de} onClick={() => onPick(code)}>
            <img src={symbol(code)} alt="" />
          </button>
        ))}
      </div>
      {!found.length && <p className="hint">Kein Symbol gefunden.</p>}
    </>
  );
}
