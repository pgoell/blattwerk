// The fields for place, size and angle, and the quarter turns and flips.
import { useState } from "react";
import { Lock, LockOpen, FlipHorizontal2, FlipVertical2, RotateCcw, RotateCw, type LucideIcon } from "lucide-react";
import { bounds, drawn, frameOf, kept, norm, round, scaledGroup, signature, sized, unfit } from "../../arrange";
import { isLine, type Axis, type Block, type Box } from "../../sheet";
import { Num } from "./num";

const TURNS: [string, LucideIcon, number][] = [["Rechtsdrehung 90°", RotateCw, 90], ["Linksdrehung 90°", RotateCcw, -90], ["Horizontal spiegeln", FlipHorizontal2, 0], ["Vertikal spiegeln", FlipVertical2, 0]];

export function Place({
  sel, place, lock, setLock, from, setFrom, W, H, spin, onSize, alone,
}: {
  sel: Block[];
  place: (boxes: [string, Partial<Box>][], key?: string) => void;
  lock: boolean;
  setLock: (on: boolean) => void;
  from: "corner" | "centre";
  setFrom: (from: "corner" | "centre") => void;
  W: number;
  H: number;
  spin: (by: number) => void;
  onSize: (ids: string[]) => void;
  alone: (b: Block) => boolean;
}) {
  const [typed, setTyped] = useState<{ sig: string; w?: number; h?: number }>();
  const fixed = sel.some((b) => b.locked);
  const level = fixed || sel.some((b) => b.type === "table" || (isLine(b) && alone(b)));

  // The fields for place, size and angle, as in PowerPoint's size pane. A field shows what all the blocks share.
  // A selection with a group in it is one thing: it shows the box around it, which only moves.
  const whole = sel.some((b) => b.group);
  const box = bounds(sel);
  // Its width and height are those of its own frame, the box it has at 0 degrees, as in PowerPoint.
  const own = whole ? bounds(frameOf(sel).level) : box;
  // What the panel shows for a group's side: what was typed, while the group is as it was left, else its frame.
  const shownOwn = (side: "w" | "h") => (typed && typed.sig === signature(sel) && typed[side] !== undefined ? typed[side] : round(own[side]));
  const shared = (of: (b: Block) => number) => (whole ? undefined : sel.every((b) => of(b) === of(sel[0])) ? of(sel[0]) : undefined);
  // A picture, a symbol and a Hunderterfeld always keep their shape.
  const shaped = sel.some((b) => b.type === "image" || b.type === "symbol" || b.type === "hunderterfeld");
  const keep = lock || shaped;
  const move = (axis: Axis, to: number) => place(sel.map((b) => [b.id, { [axis]: whole ? round(b[axis] + to - box[axis]) : to }]));
  // The distance from the page's corner to where X and Y count from: nothing, or half the page in Mitte.
  const offset = (axis: "x" | "y") => (from === "centre" ? (axis === "x" ? W : H) / 2 : 0);
  const shownAt = (axis: "x" | "y", v?: number) => (v === undefined ? undefined : round(v - offset(axis)));
  // The corner stays. A group scales about its top left corner, and with the lock all of it keeps its shape.
  // Loose blocks each keep their own shape.
  // A group scaled once by `f` on its sides; the field then shows what was typed, as the frame may not land on it.
  // `to` is the value of `side` the field shows after; the other side shows its own value, scaled when both scale.
  const scaleWhole = (side: "w" | "h", f: number, to: number) => {
    const both = lock || sel.some(kept);
    const out = scaledGroup(sel, ...(side === "w" ? [f, both ? f : 1] : [both ? f : 1, f]) as [number, number]);
    const other = side === "w" ? "h" : "w";
    const rest = both ? round(shownOwn(other) * f) : shownOwn(other);
    setTyped({ sig: signature(out), ...(side === "w" ? { w: to, h: rest } : { w: rest, h: to }) });
    place(out.map(sized));
  };
  const resize = (side: "w" | "h", to: number) => {
    const other = side === "w" ? "h" : "w";
    // A group of flat lines has no height to scale from.
    if (to <= 0 || (whole && own[side] <= 0)) return;
    onSize(sel.map((b) => b.id));
    if (whole) {
      scaleWhole(side, to / shownOwn(side), to);
      return;
    }
    place(sel.map((b) => [b.id, { [side]: to, ...(kept(b) && b[side] > 0 && { [other]: round((b[other] * to) / b[side]) }), ...unfit(b) } as Partial<Box>]));
  };
  // A percent scales the box from its top left corner, or about the group's; a loose block keeps its own shape when it is kept.
  const percent = (side: "w" | "h", p: number) => {
    if (!(p > 0)) return;
    onSize(sel.map((b) => b.id));
    const f = p / 100;
    // The side named scales; the other too when the shape is kept.
    const factors = (both: boolean): [number, number] => (side === "w" ? [f, both ? f : 1] : [both ? f : 1, f]);
    if (whole) {
      scaleWhole(side, f, shownOwn(side) * f);
      return;
    }
    // A loose block scales its own width and height, as its Breite and Höhe do, also when it is turned.
    const out = sel.map((b) => (([sx, sy]) => ({ ...b, w: round(b.w * sx), h: round(b.h * sy) }))(factors(kept(b))));
    place(out.map(sized));
  };
  // A picture goes back to the size it had when it came in, as the editor sets a new one: uncropped, cut
  // shares taken off, its place kept.
  const [only] = sel;
  const pic = sel.length === 1 && only.type === "image" ? only : undefined;
  const original = () => {
    if (!pic) return;
    const { ratio, cut } = pic.props;
    const w0 = Math.min(100, 100 * ratio);
    place([[pic.id, { w: round(w0 * (1 - cut[0] - cut[2])), h: round((w0 / ratio) * (1 - cut[1] - cut[3])) }]]);
  };
  const turned = sel.find((b) => !isLine(b));
  const angle = whole ? turned?.angle ?? 0 : shared((b) => b.angle ?? 0);
  const turn = (to: number) => norm(to) !== angle && (whole ? spin(norm(to) - (angle ?? 0)) : place(sel.map((b) => [b.id, { angle: norm(to) }])));
  return (
      <div className="geo">
        <h2>Position und Größe in mm</h2>
        <label>
          von
          <select aria-label="von" value={from} onChange={(e) => setFrom(e.target.value as "corner" | "centre")}>
            <option value="corner">Ecke oben links</option>
            <option value="centre">Mitte</option>
          </select>
        </label>
        <span />
        {/* In Mitte the place counts from the page's centre: a block at 15 mm shows -90 in a page 210 mm wide. */}
        <Num label="X" units value={shownAt("x", whole ? box.x : shared((b) => b.x))} disabled={fixed} onCommit={(n) => move("x", n + offset("x"))} />
        <Num label="Y" units value={shownAt("y", whole ? box.y : shared((b) => b.y))} disabled={fixed} onCommit={(n) => move("y", n + offset("y"))} />
        <Num label="Breite" units value={whole ? shownOwn("w") : shared((b) => b.w)} disabled={fixed || sel.some((b) => isLine(b) && alone(b))} onCommit={(n) => resize("w", n)} />
        <Num label="Höhe" units value={whole ? shownOwn("h") : shared((b) => b.h)} disabled={fixed || sel.some((b) => isLine(b) && alone(b))} onCommit={(n) => resize("h", n)} />
        <Num label="Drehung" value={angle} disabled={level} onCommit={turn} />
        <span>
          °
          <button className={keep ? "ib on" : "ib"} aria-label="Seitenverhältnis sperren" title="Seitenverhältnis sperren" aria-pressed={keep} disabled={fixed || shaped} onClick={() => setLock(!lock)}>
            {keep ? <Lock size={14} aria-hidden /> : <LockOpen size={14} aria-hidden />}
          </button>
        </span>
        {/* A percent always reads 100: it scales the selection once and shows 100 again. */}
        <Num label="Breite %" value={100} disabled={fixed} onCommit={(p) => percent("w", p)} />
        <Num label="Höhe %" value={100} disabled={fixed} onCommit={(p) => percent("h", p)} />
        {pic && (
          <button aria-label="Originalgröße" title="Originalgröße" disabled={fixed} onClick={original}>
            Originalgröße
          </button>
        )}
      </div>
  );
}

export function Turns({ sel, alone, spin, mirror }: { sel: Block[]; alone: (b: Block) => boolean; spin: (by: number) => void; mirror: (axis: Axis) => void }) {
  const fixed = sel.some((b) => b.locked);
  const level = fixed || sel.some((b) => b.type === "table" || (isLine(b) && alone(b)));
  const plain = fixed || !sel.some((b) => !alone(b) || b.type === "image" || b.type === "symbol" || b.type === "shape" || drawn(b));
  return (
    <>
      <h2>Drehen</h2>
      <div className="seg">
        {TURNS.map(([label, Icon, by]) => (
          <button key={label} aria-label={label} title={label} disabled={by ? level : plain} onClick={() => (by ? spin(by) : mirror(label[0] === "H" ? "x" : "y"))}>
            <Icon size={14} aria-hidden />
          </button>
        ))}
      </div>
    </>
  );
}
