// Guide lines, and the handles on a line or a shape.
import { useRef, type PointerEvent } from "react";
import { adjusted, far, handleOf, type Axis, type Block, type Corner, type ShapeBlock, type TextProps } from "../../sheet";
import { adjustable, bounds, frameOf, hull, scaledGroup, sized as resized, unfit as unfitted } from "../Format";
import { turnedAt, KEEP, CENTRE, round } from "./palette";
import { useTable } from "./useTable";

export function useGuides(session: ReturnType<typeof useTable>) {
  const own = session.own;
  const at = session.at;
  const reach = session.reach;
  const right = session.right;
  const mod = session.mod;
  const setGuide = session.setGuide;
  const desk = session.desk;
  const adjusting = session.adjusting;
  const start = session.start;
  const guides = session.guides;
  const page = session.page;
  const W = session.W;
  const H = session.H;
  const cell = session.cell;
  const mine = session.mine;
  const loose = session.loose;
  const k = session.k;
  const sel = session.sel;
  const from = session.from;
  const turnedLine = session.turnedLine;
  const xs = session.xs;
  const ys = session.ys;
  const turn = session.turn;
  const change = session.change;
  const rules = session.rules;
  const place = session.place;
  const seen = session.seen;
  const same = session.same;
  const point = session.point;
// The guide closest to a point, if one lies within the snap distance.
  const near = (at: number, guides: number[]) => guides.filter((g) => Math.abs(g - at) < 6 / k).sort((a, b) => Math.abs(a - at) - Math.abs(b - at))[0];
  // Moves one end of a line with the pointer; the other end stays, or with Ctrl the middle does. It snaps to the
  // guides a block drag snaps to, and to the point that stays, which makes the line level or upright.
  function stretch(e: PointerEvent, b: ShapeBlock, end: boolean) {
    if (!e.currentTarget.hasPointerCapture(e.pointerId)) return;
    const mid = (mod & CENTRE) > 0;
    let fx = mid ? b.x + b.w / 2 : b.x + (far(b, 1, !end) ? b.w : 0);
    let fy = mid ? b.y + b.h / 2 : b.y + (far(b, 0, !end) ? b.h : 0);
    const at = point(e);
    // Shift turns the line in steps of 45 degrees and leaves the guides alone.
    const turn = (Math.round(Math.atan2(at[1] - fy, at[0] - fx) / (Math.PI / 4)) * Math.PI) / 4;
    const reach = Math.hypot(at[0] - fx, at[1] - fy);
    const gx = mod & KEEP ? fx + Math.cos(turn) * reach : near(at[0], loose ? [] : [fx, ...xs]);
    const gy = mod & KEEP ? fy + Math.sin(turn) * reach : near(at[1], loose ? [] : [fy, ...ys]);
    setGuide(mod & KEEP ? [] : [gx, gy]);
    const [px, py] = [gx ?? at[0], gy ?? at[1]];
    if (mid) [fx, fy] = [2 * fx - px, 2 * fy - py];
    const from = ((py > fy !== end ? "s" : "n") + (px > fx !== end ? "e" : "w")) as Corner;
    const box = { x: round(Math.min(px, fx)), y: round(Math.min(py, fy)), w: round(Math.abs(px - fx)), h: round(Math.abs(py - fy)) };
    change((bs) => bs.map((o) => (o.id === b.id ? { ...b, ...box, props: { ...b.props, from } } : o)), "drag");
  }
  // How far down the adjust handle of a triangle, a rounded box or a bubble stands from its point, in mm: 12 px inside
  // the box, clear of Moveable's handles on its edge.
  const pullOf = (kind?: string) => (kind === "triangle" || kind === "rounded" ? 12 / k : kind === "bubble" ? -12 / k : 0);
  // A bubble's handle is pulled into the box only while its tip lies in the box: outside, the handle stands on the tip.
  const pullAt = (b: Block, [x, y]: [number, number]) => {
    const kind = (b.props as TextProps).kind;
    return kind === "bubble" && (x < 0 || y < 0 || x > b.w || y > b.h) ? 0 : pullOf(kind);
  };
  // Where the adjust handle of a block stands on the page, in mm: its point in the block's own frame, flipped and turned.
  function adjustAt(b: Block): [number, number] {
    const p = b.props as TextProps;
    const [lx, ly] = handleOf(p.kind, b.w, b.h, p)!;
    const [cx, cy] = [b.x + b.w / 2, b.y + b.h / 2];
    const [dx, dy] = [lx - b.w / 2, ly + pullAt(b, [lx, ly]) - b.h / 2];
    return turnedAt([cx + dx * (b.flipX ? -1 : 1), cy + dy * (b.flipY ? -1 : 1)], b.angle ?? 0, [cx, cy]);
  }
  // Moves the point of a picked speech bubble, star or triangle with the pointer, and sets its props on each picked block of the same kind.
  function adjust(e: PointerEvent, b: Block) {
    // A pointer with no button down holds nothing, whatever it held before.
    if (!e.buttons || (!e.currentTarget.hasPointerCapture(e.pointerId) && adjusting.current !== e.pointerId)) return;
    const p = b.props as TextProps;
    const [cx, cy] = [b.x + b.w / 2, b.y + b.h / 2];
    const [px, py] = turnedAt(point(e) as [number, number], -(b.angle ?? 0), [cx, cy]);
    const [fx, fy] = [cx + (px - cx) * (b.flipX ? -1 : 1), cy + (py - cy) * (b.flipY ? -1 : 1)];
    const raw: [number, number] = [fx - b.x, fy - b.y];
    const local: [number, number] = [raw[0], raw[1] - pullAt(b, raw)];
    const props = adjusted(p.kind, b.w, b.h, local);
    const same = new Set(sel.filter((o) => adjustable(o) && !o.locked && (o.props as TextProps).kind === p.kind).map((o) => o.id));
    change((bs) => bs.map((o) => (same.has(o.id) ? ({ ...o, props: { ...o.props, ...props } } as Block) : o)), "drag");
  }
  // Resizes a group from the boxes it began with. The corner opposite the dragged one stays, or with Ctrl the middle,
  // and the group keeps its shape, as Moveable's groups do, so every line keeps its angle. A group can shrink to a
  // tenth, not flip.
  function scale(e: PointerEvent, right: boolean, low: boolean) {
    if (!e.currentTarget.hasPointerCapture(e.pointerId)) return;
    // A turned group scales in its own frame: the pointer turns back to it, and the factor is taken there.
    const { turn, about, level } = turnedLine ? frameOf(start.current) : { turn: 0, about: [0, 0] as [number, number], level: start.current };
    const { x, y, w, h } = turnedLine ? bounds(level) : hull(level);
    const [px, py] = turn ? turnedAt(point(e) as [number, number], -turn, about) : point(e);
    const half = mod & CENTRE ? 2 : 1;
    const [fx, fy] = half > 1 ? [x + w / 2, y + h / 2] : [right ? x : x + w, low ? y : y + h];
    const [sw, sh] = [(right ? w : -w) / half, (low ? h : -h) / half];
    let s = Math.max(0.1, w && (px - fx) / sw, h && (py - fy) / sh);
    if (turn) {
      setGuide([]);
      place(scaledGroup(start.current, s, s, [fx, fy]).map(resized), "drag");
      return;
    }
    // The dragged corner snaps to the guides a block drag snaps to. The group keeps its shape, so only the nearer
    // of the two guides holds it.
    const [mx, my] = [fx + sw * s, fy + sh * s];
    const gx = w ? near(mx, xs.filter((g) => (g - fx) / sw >= 0.1)) : undefined;
    const gy = h ? near(my, ys.filter((g) => (g - fy) / sh >= 0.1)) : undefined;
    const onX = gx !== undefined && (gy === undefined || Math.abs(gx - mx) <= Math.abs(gy - my));
    if (onX) s = (gx - fx) / sw;
    else if (gy !== undefined) s = (gy - fy) / sh;
    setGuide(onX ? [gx] : [undefined, gy]);
    // Each size comes from its block's two edges, so the edge on the guide lands exactly on it.
    place(
      start.current.map((b) => {
        const [bx, by] = [round(fx + (b.x - fx) * s), round(fy + (b.y - fy) * s)];
        return [b.id, { x: bx, y: by, w: round(fx + (b.x + b.w - fx) * s - bx), h: round(fy + (b.y + b.h - fy) * s - by), ...unfitted(b) }];
      }),
      "drag",
    );
  }

  // A new guide line starts in the middle of what the desk shows, clear of a guide already there.
  function rule(axis: Axis) {
    let at = axis === "x" ? W / 2 : Math.max(0, Math.min(H, Math.round(seen(desk.current!.clientHeight / 2))));
    while ([...guides[axis], ...mine[axis]].includes(at)) at += 10;
    rules(own ? page : undefined, (g) => ({ ...g, [axis]: [...g[axis], at] }));
  }
  // A guide line moves with its tab, in steps of the grid or of a millimetre. `n` is the page of a page's own line.
  function slide(e: PointerEvent, axis: Axis, i: number, n?: number) {
    if (!e.currentTarget.hasPointerCapture(e.pointerId)) return;
    const at = point(e)[axis === "x" ? 0 : 1];
    const by = loose ? 0.01 : cell || 1;
    const to = round(Math.round(at / by) * by);
    rules(n, (g) => ({ ...g, [axis]: g[axis].map((o, j) => (j === i ? to : o)) }), "drag");
  }
  // The tab of a guide line held now: its page, axis and number.
  const sliding = useRef("");
  // Let go off the page, a guide line is gone. Its place is read from the document as it stands, not from the last
  // render: the pointer may be let go before the page has drawn its last move (#525).
  function drop(axis: Axis, i: number, n?: number) {
    const on = (at: number) => at >= 0 && at <= (axis === "x" ? W : H);
    rules(n, (g) => (on(g[axis][i]) ? g : { ...g, [axis]: g[axis].filter((_, j) => j !== i) }), "drag");
  }

    return Object.assign(session, { near, stretch, pullOf, pullAt, adjustAt, adjust, scale, rule, slide, sliding, drop });
}
