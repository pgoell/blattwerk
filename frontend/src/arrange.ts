// Where a selection sits once it is turned, scaled or mirrored, and which looks the picked words share.
import { PT, boxed, dir, far, isLine, parasOf, type Axis, type Block, type Box, type Corner, type ShapeBlock } from "./sheet";
import type { Picked } from "./pages/Field";

export const round = (n: number) => Math.round(n * 100) / 100;
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
export const hull = (bs: Box[]) => bounds(bs.map((b) => outline({ ...b, x: b.x - lean(b), y: b.y + lean(b) })));
// A quarter turn clockwise of the blocks as one. The box around them goes on its side about its middle, to the
// hundredth: half a hundredth too many goes away one time and comes back the next. In it each block's centre goes
// round and keeps its distances to the edges, so all stays on the hundredths. A line has no angle: its box goes on
// its side, and the line starts at the next corner.
const quarter = (bs: Block[]): Block[] => {
  const all = hull(bs);
  const d = Math.trunc(Math.round((all.w - all.h) * 100) / 2) / 100;
  return bs.map((b) => {
    const to = isLine(b) ? { ...b, w: b.h, h: b.w, props: { ...b.props, from: NEXT[b.props.from ?? "nw"] } } : { ...b, angle: norm((b.angle ?? 0) + 90) };
    // As far from the left as the centre was from the bottom, and as far from the top as it was from the left.
    const x = all.x + d + (all.y + all.h - (b.y + lean(b) + b.h / 2));
    const y = all.y - d + (b.x - lean(b) + b.w / 2 - all.x);
    return { ...to, x: round(x - to.w / 2 + lean(to)), y: round(y - to.h / 2 - lean(to)) };
  });
};
// A line's start and end on the page.
const endsOf = (b: ShapeBlock) => [
  [b.x + (far(b, 1, false) ? b.w : 0), b.y + (far(b, 0, false) ? b.h : 0)],
  [b.x + (far(b, 1, true) ? b.w : 0), b.y + (far(b, 0, true) ? b.h : 0)],
];
// The box a thing lines up by: a line draws its stroke round its ends and an arrow head there (a double's at both),
// so its box takes them in. Any other block lines up by its outline.
export const inked = (b: Block): Box => {
  if (!isLine(b)) return outline(b);
  const [s, e] = endsOf(b);
  const [dx, dy] = [e[0] - s[0], e[1] - s[1]];
  const len = Math.hypot(dx, dy) || 1;
  const [u, p] = [[dx / len, dy / len], [-dy / len, dx / len]];
  const sw = b.props.strokeWidth ?? 0.5;
  const head = b.props.kind === "line" ? 0 : 2 + sw * 3;
  const at = ([x, y]: number[], along: number, across: number) => [x + u[0] * along + p[0] * across, y + u[1] * along + p[1] * across];
  const points = [
    at(s, 0, sw / 2), at(s, 0, -sw / 2), at(e, 0, sw / 2), at(e, 0, -sw / 2),
    at(e, -head, head / 2), at(e, -head, -head / 2),
    ...(b.props.kind === "double" ? [at(s, head, head / 2), at(s, head, -head / 2)] : []),
    // Ticks stand 1.5 mm to each side of the ends (`Line` in sheet.tsx draws them).
    ...(b.props.ticks ? [s, e].flatMap((end) => [at(end, 0, 1.5), at(end, 0, -1.5)]) : []),
  ];
  // The length stands 2 mm over the middle, on the side that reads upright: its em box, with a char at most 0.6 em.
  if (b.props.label) {
    const fs = 12 * PT;
    const half = (`${(Math.round(len * 10) / 100).toLocaleString("de")} cm`.length * 0.6 * fs) / 2;
    const side = u[0] < 0 ? -1 : 1;
    const mid = [(s[0] + e[0]) / 2, (s[1] + e[1]) / 2];
    for (const along of [-half, half]) for (const across of [-2 - 1.2 * fs, -2 + 0.35 * fs]) points.push(at(mid, along, side * across));
  }
  const [xs, ys] = [points.map(([x]) => x), points.map(([, y]) => y)];
  const [x, y] = [Math.min(...xs), Math.min(...ys)];
  return { ...b, x, y, w: Math.max(...xs) - x, h: Math.max(...ys) - y };
};
// The blocks turned as one by `by` degrees about the middle of the box around them, as the handle turns a
// selection and PowerPoint a group: each block's centre goes round, and its angle goes on. One block turns on its
// spot. Quarters are exact, and a line goes by them only. `about` is the point to turn about, when the caller
// remembers one; without it, and for quarters, the middle of the level box around the blocks.
export const swung = (bs: Block[], by: number, about?: [number, number]): Block[] => {
  if (!about && by % 90 === 0) return Array.from({ length: (((by / 90) % 4) + 4) % 4 }).reduce<Block[]>(quarter, bs);
  const [cx, cy] = about ?? ((all) => [all.x + all.w / 2, all.y + all.h / 2])(hull(bs));
  const [c, s] = dir({ angle: by });
  const turnAbout = ([x, y]: number[]) => [cx + (x - cx) * c - (y - cy) * s, cy + (x - cx) * s + (y - cy) * c];
  return bs.map((b) => {
    if (isLine(b)) {
      // A line has no angle: its two ends go round, and its box and start follow them.
      const [[px, py], [qx, qy]] = endsOf(b).map(turnAbout);
      const from = ((py <= qy ? "n" : "s") + (px <= qx ? "w" : "e")) as Corner;
      return { ...b, x: round(Math.min(px, qx)), y: round(Math.min(py, qy)), w: round(Math.abs(px - qx)), h: round(Math.abs(py - qy)), props: { ...b.props, from } };
    }
    const [x, y] = [b.x + b.w / 2 - cx, b.y + b.h / 2 - cy];
    return { ...b, x: round(cx + x * c - y * s - b.w / 2), y: round(cy + x * s + y * c - b.h / 2), angle: norm((b.angle ?? 0) + by) };
  });
};
// The blocks scaled about the point (ox, oy): each one's place and size go with the factors. A turned block keeps its
// centre's way from the point and its own axes: its width takes the factor of the axis it lies along.
export const scaled = (bs: Block[], sx: number, sy: number, [ox, oy]: [number, number]): Block[] =>
  bs.map((b) => {
    if (isLine(b) || !b.angle) return { ...b, x: round(ox + (b.x - ox) * sx), y: round(oy + (b.y - oy) * sy), w: round(b.w * sx), h: round(b.h * sy) };
    const [c, s] = dir(b).map(Math.abs);
    const [w, h] = c >= s ? [b.w * sx, b.h * sy] : [b.w * sy, b.h * sx];
    const [cx, cy] = [ox + (b.x + b.w / 2 - ox) * sx, oy + (b.y + b.h / 2 - oy) * sy];
    return { ...b, x: round(cx - w / 2), y: round(cy - h / 2), w: round(w), h: round(h) };
  });
// A group that is turned scales in its own frame: it goes level about its middle, scales there, and turns back, so
// a line in it still lies along the box. A group is turned when all its blocks but the lines share one angle; one with
// blocks turned each their own way scales along the page, each block by the axis it lies along.
// `at` is the point that stays, in the level frame: the level box's top left corner unless one is given.
export const scaledGroup = (bs: Block[], sx: number, sy: number, at?: [number, number]): Block[] => {
  const { turn, about, level } = frameOf(bs);
  const lb = bounds(level);
  const o = at ?? [lb.x, lb.y];
  return turn ? swung(scaled(level, sx, sy, o), turn, about) : scaled(bs, sx, sy, o);
};
// A group's own frame: its blocks laid level about its middle when it is turned, as they are when it is not.
export const frameOf = (bs: Block[]) => {
  const angles = new Set(bs.filter((b) => !isLine(b)).map((b) => b.angle ?? 0));
  const turn = angles.size === 1 ? [...angles][0] : 0;
  const all = hull(bs);
  const about: [number, number] = [all.x + all.w / 2, all.y + all.h / 2];
  return { turn, about, level: turn ? swung(bs, -turn, about) : bs };
};
// A block's new place and size. A line in a turned group may start at another corner after the scale: it takes that too.
export const sized = (b: Block): [string, Partial<Box>] => [b.id, { x: b.x, y: b.y, w: b.w, h: b.h, ...(isLine(b) && ({ props: b.props } as Partial<Box>)), ...unfit(b) }];
// A box fitted to its text that the teacher sizes by hand keeps that size: its fit goes off in the same step.
export const unfit = (b: Block): Partial<Box> => (boxed(b)?.fit === true ? ({ props: { ...b.props, fit: undefined } } as Partial<Box>) : {});
// A block that keeps its own shape: its lock, or a picture, a symbol and a Hunderterfeld.
export const kept = (b: Block) => !!b.keep ||b.type === "image" || b.type === "symbol" || b.type === "hunderterfeld";
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
// What a size typed on these blocks is remembered by: their places, sizes and angles.
export const signature = (bs: Block[]) => JSON.stringify(bs.map((b) => [b.id, b.x, b.y, b.w, b.h, b.angle ?? 0]));

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
// Whether a block has an adjust handle: a drawn outline, or a rounded box, whose handle sets its corner.
export const adjustable = (b: Block) => drawn(b) || ((b.type === "shape" || b.type === "text") && b.props.kind === "rounded");
