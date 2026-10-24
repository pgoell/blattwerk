// Grouping, the stack, and lining blocks up.
import { useRef, type MouseEvent as Click } from "react";
import { flushSync } from "react-dom";
import type { OnDrag } from "react-moveable";
import { K, dir, sum, type Axis, type Block } from "../../sheet";
import { next, sized } from "../../cells";
import { bounds, inked, outline } from "../Format";
import { SLOP, KEEP, round, idOf, span } from "./palette";
import { useClipboard } from "./useClipboard";

export function useArrange(session: ReturnType<typeof useClipboard>) {
  const hist = session.hist;
  const at = session.at;
  const ids = session.ids;
  const setIds = session.setIds;
  const rest = session.rest;
  const finger = session.finger;
  const part = session.part;
  const side = session.side;
  const mod = session.mod;
  const desk = session.desk;
  const ahead = session.ahead;
  const touch = session.touch;
  const came = session.came;
  const owed = session.owed;
  const start = session.start;
  const guides = session.guides;
  const blocks = session.blocks;
  const W = session.W;
  const H = session.H;
  const last = session.last;
  const k = session.k;
  const sel = session.sel;
  const from = session.from;
  const things = session.things;
  const among = session.among;
  const sizable = session.sizable;
  const boxes = session.boxes;
  const frame = session.frame;
  const group = session.group;
  const across = session.across;
  const down = session.down;
  const top = session.top;
  const still = session.still;
  const xs = session.xs;
  const ys = session.ys;
  const change = session.change;
  const place = session.place;
  const wide = session.wide;
  const joinable = session.joinable;
  const splittable = session.splittable;
  const whole = (...a: any[]) => (session as Record<string, any>).whole(...a);
  const deskStep = (...a: any[]) => (session as Record<string, any>).deskStep(...a);
function join() {
    if (!joinable) return;
    const id = crypto.randomUUID();
    const inside = new Set(wide.map((b) => b.id));
    // The group lies where its topmost block lay: its blocks keep their order, and nothing lies between them.
    const order = [...blocks].sort((a, b) => a.z - b.z);
    const members = order.filter((b) => inside.has(b.id));
    const last = order.indexOf(members.at(-1)!);
    const stack = [...order.slice(0, last).filter((b) => !inside.has(b.id)), ...members, ...order.slice(last + 1)];
    const z = new Map(stack.map((b, i) => [b.id, i + 1]));
    change((bs) => bs.map((b) => ({ ...b, z: z.get(b.id)!, ...(inside.has(b.id) && { group: [id, ...(b.group ?? [])] }) })));
    setIds(wide.map((b) => b.id));
  }
  // Ungrouping takes the outermost group away; the groups in it stay.
  function split() {
    if (!splittable) return;
    place(wide.map((b) => [b.id, { group: b.group && b.group.length > 1 ? b.group.slice(1) : undefined }]));
    setIds(wide.map((b) => b.id));
  }
  // To the front or the back, as in PowerPoint: a part of a group moves within that group, a whole group as one thing.
  // With `one` a single step instead: over the next thing that does not move, a block or a whole group.
  // The new stack from back to front, or nothing where all already lies there.
  function stacked(front: boolean, one = false) {
    const whole = (g: string) => blocks.every((b) => !b.group?.includes(g) || ids.includes(b.id));
    // What a block moves in: its innermost group that is not picked whole, or the page.
    const level = (b: Block) => b.group?.filter((g) => !whole(g)).at(-1);
    const order = [...blocks].sort((a, b) => a.z - b.z);
    let stack = order;
    for (const g of new Set(sel.map(level))) {
      // The blocks of this level swap places among themselves, so the stack around them stays as it is.
      const part = stack.filter((b) => !g || b.group?.includes(g));
      const moved = part.filter((b) => sel.includes(b) && level(b) === g);
      const rest = part.filter((b) => !moved.includes(b));
      let next = front ? [...rest, ...moved] : [...moved, ...rest];
      if (one) {
        // What steps as one thing in this level: a block, or a group right inside it.
        const top = (b: Block) => b.group?.[g ? b.group.indexOf(g) + 1 : 0] ?? b.id;
        const units: Block[][] = [];
        for (const b of part) {
          if (units.length && top(units.at(-1)![0]) === top(b)) units.at(-1)!.push(b);
          else units.push([b]);
        }
        // From the end they step towards, so several keep their order. Backward is forward on the stack turned over.
        if (!front) units.reverse();
        for (let i = units.length - 2; i >= 0; i--) {
          if (moved.includes(units[i][0]) && !moved.includes(units[i + 1][0])) [units[i], units[i + 1]] = [units[i + 1], units[i]];
        }
        next = (front ? units : units.reverse()).flat();
      }
      stack = stack.map((b) => (part.includes(b) ? next.shift()! : b));
    }
    if (!stack.every((b, i) => b === order[i])) return stack;
  }
  // What already lies there leaves nothing to undo.
  function raise(front: boolean, one = false) {
    const stack = stacked(front, one);
    if (!stack) return;
    const z = new Map(stack.map((b, i) => [b.id, i + 1]));
    place(blocks.map((b) => [b.id, { z: z.get(b.id)! }]));
  }
  // A button of the order that greys with its press gives the focus to its pair, which the press made live, so who
  // works the panel with the keys stays where they were.
  function layer(e: Click<HTMLButtonElement>, front: boolean, one = false) {
    const el = e.currentTarget;
    const had = document.activeElement === el;
    flushSync(() => raise(front, one));
    if (had && el.disabled) ((el.nextElementSibling ?? el.previousElementSibling) as HTMLElement | null)?.focus();
  }

  // Puts the blocks where they belong, rounded. What already lies there leaves nothing to undo.
  function bring(to: [Block, Partial<Record<"x" | "y" | "w" | "h", number>>][]) {
    const boxes = to.map(([b, box]) => [b, Object.entries(box).map(([side, n]) => [side as "x" | "y" | "w" | "h", round(n)] as const)] as const);
    if (boxes.every(([b, box]) => box.every(([side, n]) => round(b[side]) === n))) return;
    place(boxes.map(([b, box]) => [b.id, Object.fromEntries(box)]));
  }
  // A thing lines up by the box around its outlines, a turned block's too, and moves whole.
  function align(axis: Axis, at: number) {
    const size = axis === "x" ? "w" : "h";
    const boxes = things.map((t) => bounds(t.map(inked)));
    // One thing lines up with the page. Several do so with each other, or with the page when the switch says so.
    const lo = among ? Math.min(...boxes.map((b) => b[axis])) : 0;
    const hi = among ? Math.max(...boxes.map((b) => b[axis] + b[size])) : axis === "x" ? W : H;
    bring(things.flatMap((t, i) => t.map((b) => [b, { [axis]: b[axis] + lo + (hi - lo - boxes[i][size]) * at - boxes[i][axis] }])));
  }
  // As wide as the widest, or as high as the highest, by the outlines. Each outline keeps its corner; a picture and a
  // symbol keep their shape.
  function same(side: "w" | "h") {
    const other = side === "w" ? "h" : "w";
    const to = Math.max(...sizable.map((b) => outline(b)[side]));
    bring(
      sizable.map((b) => {
        const [c, s] = dir(b).map(Math.abs);
        // Of a turned block the side that lies more along this one grows, until the outline is that large.
        const along = c >= s ? side : other;
        const across = along === "w" ? "h" : "w";
        const k = to / outline(b)[side];
        const sized = b.type === "image" || b.type === "symbol" || b.type === "hunderterfeld" ? { ...b, w: b.w * k, h: b.h * k } : { ...b, [along]: (to - b[across] * Math.min(c, s)) / Math.max(c, s) };
        const [was, now] = [outline(b), outline(sized)];
        return [b, { x: sized.x + was.x - now.x, y: sized.y + was.y - now.y, w: sized.w, h: sized.h }];
      }),
    );
  }
  function distribute(axis: Axis) {
    const size = axis === "x" ? "w" : "h";
    const row = things.map((t) => ({ t, box: bounds(t.map(inked)) })).sort((a, b) => a.box[axis] - b.box[axis]);
    // Between the outer things, or between the page's edges. One thing goes to the middle of the frame.
    const lo = among ? Math.min(...row.map((r) => r.box[axis])) : 0;
    const hi = among ? Math.max(...row.map((r) => r.box[axis] + r.box[size])) : axis === "x" ? W : H;
    const sum = row.reduce((total, r) => total + r.box[size], 0);
    const gap = row.length > 1 ? (hi - lo - sum) / (row.length - 1) : 0;
    let next = row.length > 1 ? lo : (lo + hi - sum) / 2;
    bring(
      row.flatMap(({ t, box }) => {
        const by = next - box[axis];
        next += box[size] + gap;
        return t.map((b) => [b, { [axis]: b[axis] + by }]);
      }),
    );
  }

  // Moveable works in whole pixels of the layout and leaves what it snaps up to two off the guide.
  // This is how far to move so that the nearest of `parts` that close lies exactly on it.
  const pull = (at: number, parts: number[], guides: number[]) =>
    parts
      .flatMap((part) => guides.map((g) => g - at - part))
      .filter((d) => Math.abs(d) < 2 / K)
      .sort((a, b) => Math.abs(a) - Math.abs(b))[0] ?? 0;
  const edge = (at: number, guides: number[]) => at + pull(at, [0], guides);

  // Moveable reports px of the layout, the document keeps mm. It reads the new size back at once, so render before returning.
  // A group snaps as one box, by its edges or its centre, and all its blocks move by the same amount.
  const drag = (events: OnDrag[], finger: { clientX: number; clientY: number } = events[0]) => {
    edgeScroll(finger.clientX, finger.clientY);
    // A finger that holds never rests still: nothing moves until it has left where it came down. Once a block has
    // moved, the blocks are new ones, and they follow the finger back there too. Of a group only the event of the
    // whole says where the finger is: those of its blocks say where a snap would put them.
    // Moveable says nothing more while a snap holds the blocks, so what is dropped here is kept for the finger's
    // own move to bring back once it has left.
    const still = touch.current && blocks.includes(start.current[0]) && Math.hypot(finger.clientX - came.current[0], finger.clientY - came.current[1]) <= SLOP;
    owed.current = still ? events : undefined;
    if (still) return;
    const from = events.map((e) => blocks.find((b) => b.id === idOf(e.target))!);
    // The desk's scroll has moved the blocks by `deskShift` since Moveable last measured them.
    const to = events.map((e, i) => ({ ...from[i], x: e.left / K, y: e.top / K + deskShift.current }));
    let [dx, dy] = (["x", "y"] as const).map((axis) => {
      // A turned block snaps by its outline.
      const [lo, hi] = span(to.map(outline), axis);
      return round(to[0][axis] + pull(lo, [0, (hi - lo) / 2, hi - lo], axis === "x" ? xs : ys) - from[0][axis]);
    });
    // Shift keeps the move level or upright: the shorter way from where the drag began does not count.
    if (mod & KEEP) {
      const began = start.current.find((b) => b.id === from[0].id)!;
      if (Math.abs(from[0].x + dx - began.x) >= Math.abs(from[0].y + dy - began.y)) dy = began.y - from[0].y;
      else dx = began.x - from[0].x;
    }
    flushSync(() => place(from.map((b) => [b.id, { x: round(b.x + dx), y: round(b.y + dy) }]), "drag"));
  };
  const begin = (els: Element[]) => {
    owed.current = undefined;
    ahead.current = hist.future;
    start.current = els.map((el) => blocks.find((b) => b.id === idOf(el))!);
    deskShift.current = 0;
  };
  // Near the top or the bottom of the desk a block drag scrolls it, faster the nearer the pointer is to the edge, and the
  // blocks go with it so they stay under the pointer. The scroll goes on while the pointer rests there.
  const deskShift = useRef(0);
  const deskAuto = useRef({ frame: 0, speed: 0, x: 0, y: 0, last: 0, rest: 0 });
  function edgeScroll(x: number, y: number) {
    const view = desk.current!.getBoundingClientRect();
    const zone = 40;
    const down = (y - (view.bottom - zone)) / zone;
    const up = (view.top + zone - y) / zone;
    const a = deskAuto.current;
    a.x = x;
    a.y = y;
    a.speed = (down > 0 ? Math.min(1, down) : up > 0 ? -Math.min(1, up) : 0) * 12;
    if (!a.speed) stopDeskScroll();
    else if (!a.frame) a.frame = requestAnimationFrame(deskStep);
  }
  function stopDeskScroll() {
    const a = deskAuto.current;
    cancelAnimationFrame(a.frame);
    a.frame = 0;
    a.speed = 0;
    a.last = 0;
    a.rest = 0;
  }
    return Object.assign(session, { join, split, stacked, raise, layer, bring, align, same, distribute, pull, edge, drag, begin, deskShift, deskAuto, edgeScroll, stopDeskScroll });
}
