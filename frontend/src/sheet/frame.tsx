// Draws a text or a shape, and a line or an arrow.

import { entries } from "../bank";
import { PT } from "../height";
import { mixed } from "../scramble";
import { pairOf, Bows } from "./bows";
import { flipped } from "./box";
import { useBreaks, Words } from "./context";
import { linesIn, fitText, leastOf, cutAt, textIn } from "./fit";
import { inset, fontOf, traceOf, INK, FONTS, SIDE, DOTTED_SIDE, fadeOf, fadeMask, textStyle } from "./look";
import { Rich } from "./rich";
import { dashes, gapWidth, fitOf, OUTLINES, tailReach, radiusOf, Bank, classes, gapVar, clear, tint, Dashes, POINTS, Outline, Ring } from "./shape";
import { type ShapeBlock, far, type TextBlock, boxed, parasOf, shownParas, listColsOf, holesOf, lineOf } from "./text";
import { type ReactNode, useContext, useRef, useState, useLayoutEffect, useEffect, type CSSProperties } from "react";

// Drawn from the start corner along its own axis; a wide unseen stroke is what a finger grabs. The length stands
// over the middle, turned so it never reads upside down.
export function Line({ block, k, solved }: { block: ShapeBlock; k: number; solved: boolean }) {
  const { kind, stroke, strokeOpacity, strokeWidth, dash, ticks, label } = block.props;
  const [x, y] = [far(block, 1, false) ? block.w : 0, far(block, 0, false) ? block.h : 0];
  const angle = (Math.atan2(block.h - 2 * y, block.w - 2 * x) * 180) / Math.PI;
  const length = Math.hypot(block.w, block.h);
  const head = kind === "line" ? 0 : 2 + strokeWidth * 3;
  // A double arrow has a head at its start too.
  const tail = kind === "double" ? head : 0;
  return (
    <svg>
      <g transform={`scale(${k}) translate(${x} ${y}) rotate(${angle})`} stroke={stroke} strokeOpacity={strokeOpacity} strokeWidth={strokeWidth} fill={stroke}>
        <line x2={length} stroke="transparent" strokeWidth={10} />
        <line x1={tail || undefined} x2={length - head} strokeDasharray={dashes(dash, strokeWidth)} strokeLinecap={dash === "dotted" ? "round" : undefined} />
        {/* The heads fade with the line; its length above it stays solid. */}
        {head > 0 && <polygon stroke="none" fillOpacity={strokeOpacity} points={`${length},0 ${length - head},${-head / 2} ${length - head},${head / 2}`} />}
        {tail > 0 && <polygon stroke="none" fillOpacity={strokeOpacity} points={`0,0 ${tail},${-tail / 2} ${tail},${tail / 2}`} />}
        {ticks && [...(tail ? [] : [0]), ...(head ? [] : [length])].map((at) => <line key={at} x1={at} x2={at} y1={-1.5} y2={1.5} />)}
        {(label === "show" || (label === "key" && solved)) && (
          <text x={length / 2} y={-2} transform={Math.abs(angle) > 90 ? `rotate(180 ${length / 2} 0)` : undefined} textAnchor="middle" fontFamily="Andika" fontSize={12 * PT} stroke="none" fill={label === "key" ? "#c0392b" : undefined}>
            {(Math.round(length * 10) / 100).toLocaleString("de")} cm
          </text>
        )}
      </g>
    </svg>
  );
}

export const UP = { top: "flex-start", middle: "center", bottom: "flex-end" };
// A text or a shape with its text. The editor passes the field the text is typed in.
export function Frame({ block, k, solved, children }: { block: TextBlock | ShapeBlock; k: number; solved: boolean; children?: ReactNode }) {
  const p = boxed(block)!;
  const breaks = useBreaks(p.breaks);
  const tints = pairOf(p.tints);
  const width = gapWidth(p.gapWidth);
  // A linked text draws the sheet's Lernwörter, one to a paragraph, in columns, and grows to hold them. Its own text
  // rests, and so do the solution words of that text.
  const sheet = useContext(Words);
  const linked = p.list === true;
  // A bubble keeps its lowest quarter for its tail: its text lies in a row three times as high as the empty one under
  // it, so the body holds it however much there is. Flipped top to bottom the tail is the top quarter, and the empty
  // row lies over the text (`.frame.tailed` in styles.css names the row of the text).
  const tailed = p.kind === "bubble";
  const words = !linked && typeof p.bank === "number" && Number.isFinite(p.bank) ? entries(parasOf(p)) : [];
  const paras = shownParas(p, sheet);
  const cols = linked ? listColsOf(p) : undefined;
  // Lückenwörter: every hidden letter is a gap of its own, and a linked text with them takes no scrambled words.
  const holes = linked && holesOf(p) !== undefined;
  // A sheet may come from anywhere: a mix that is no number, or a line that is neither word, draws the plain text.
  const scramble = typeof p.mix === "number" && Number.isFinite(p.mix) && !holes;
  const line = lineOf(p);
  const [down, across, edge] = inset(p, block.type === "shape");
  // Only a shape made since #128 keeps its text inside its outline: one saved before prints all its text as it did.
  const [fitTop, fitRight, fitBottom, fitLeft] = p.inside === true ? fitOf(p.kind, block.w, block.h, block.flipY, p, block.flipX) : [0, 0, 0, 0];
  // Such a shape never grows for its text: its type shrinks to fit the inner box (see `fitText`).
  const inside = p.inside === true && (p.kind === "circle" || p.kind === "triangle" || p.kind === "star");
  // The ink of the font that a line of this spacing does not hold reaches out of the paragraph: the clip and the padding
  // reach `up` and `down` em further, so no dot and no foot is lost (#487). A line centred on the middle of the
  // line box, which lies `c` em above the baseline, holds the ink from `s / 2` em each side of that middle.
  const font = fontOf(p.font);
  const s = typeof p.spacing === "number" && Number.isFinite(p.spacing) ? p.spacing : 1.3;
  // Under a fiftieth of the size it counts as none: Andika's lowest sign reaches 0.015 em out of a line of 1.3, less
  // than a pixel at any size a sheet uses, and its texts stay as sheets saved before drew them.
  const reach = (v: number) => (v < 0.02 ? 0 : v);
  // An outline stands half its stroke (.07em) outside the letter: 0.035 em each way, past the threshold.
  const stroke = traceOf(p) === "outline" ? 0.035 : 0;
  const above = reach(Math.max(0, INK[font][0] - FONTS[font][2] - s / 2)) + stroke;
  const below = reach(Math.max(0, INK[font][1] + FONTS[font][2] - s / 2)) + stroke;
  // How far a joined script's letters reach past their place to each side, and the outline's stroke with them.
  // A plain text takes the side reach in every font whose letters reach past their place: Andika's j lost its left
  // tip at the paragraph's edge (#489). An outline takes it in every font, and 0.12 em at least: Andika's
  // j reaches further in its outline than the upright cut's measure says. A slanted text leans 0.15 em further.
  // A dotted look takes the dotted cut's reach the same way (DOTTED_SIDE).
  const dotted = traceOf(p) === "dotted";
  const wide = Math.max(SIDE[font] ?? 0, stroke > 0 ? 0.12 : 0, dotted ? DOTTED_SIDE : 0);
  const joined = ["grund", "va", "sas", "la"].includes(font);
  const side = stroke > 0 || dotted || wide > 0 ? wide + stroke + (p.italic ? 0.15 : 0) : 0;
  // A pixel more each way (below): a browser smooths the edge of a letter over the row beside it.
  const tight = above > 0 || below > 0 || side > 0;
  // A print font's plain text is tight for its sides alone (#489): above and below it cuts where it did.
  const level = above > 0 || below > 0 || stroke > 0 || dotted || joined;
  // An outline's stroke and a dotted cut's dots reach a pixel past the measured ink, and a pixel more with the page's
  // rounding (#503): the paragraph takes one pixel more above and below for them.
  const fringe = stroke > 0 || dotted ? 2 : 1;
  // A trace text fades along its rows: a row is the font's size times its spacing, and `--ink-up` is the room above the first.
  // The rows are the lines the text has once it is drawn (`lines`), and the block's height until then.
  const fade = fadeOf(p);
  const rowMM = p.size * PT * (p.spacing ?? 1.3);
  const frameRef = useRef<HTMLDivElement>(null);
  // The px from the frame's top where its whole lines end, when a line lies past the page's foot (see `cutAt`).
  const [cut, setCut] = useState<number>();
  const [lines, setLines] = useState<number>();
  useLayoutEffect(() => {
    const frame = frameRef.current;
    const n = fade === "rows" && frame ? linesIn(frame) : undefined;
    if (n !== undefined) setLines(n);
    // Too long even at the smallest type: the frame tells the editor by how many px, and the editor grows the shape.
    const over = inside && frame ? fitText(frame, least.current, block.h * k, floored.current) : { down: 0, across: 1, cut: false };
    // Zero when it fits: the editor then lifts the page foot's warning for it. `cut` says a word does not print whole.
    if (inside && frame) frame.dispatchEvent(new CustomEvent("overfit", { bubbles: true, detail: { down: Math.max(0, over.down) / k, across: over.across, cut: over.cut } }));
  });
  // The share of its size the type may shrink to, and the shape's height in px, for a font that comes in later.
  const least = useRef(1);
  least.current = leastOf(p.size);
  // Only a shape edited since it came in (`floor`) keeps its type at 10 pt for a word too wide; a saved one prints as it did.
  const floored = useRef(false);
  floored.current = p.floor === true;
  const high = useRef(0);
  high.current = block.h * k;
  useLayoutEffect(() => {
    if (!inside) return;
    const again = () => frameRef.current && fitText(frameRef.current, least.current, high.current, floored.current);
    document.fonts.ready.then(again);
    document.fonts.addEventListener("loadingdone", again);
    return () => document.fonts.removeEventListener("loadingdone", again);
  }, [inside]);
  // The whole lines are measured after the type is fitted above, on each draw and once a font is in.
  useLayoutEffect(() => {
    if (frameRef.current) setCut(cutAt(frameRef.current));
  });
  useLayoutEffect(() => {
    const again = () => frameRef.current && setCut(cutAt(frameRef.current));
    document.fonts.ready.then(again);
    document.fonts.addEventListener("loadingdone", again);
    return () => document.fonts.removeEventListener("loadingdone", again);
  }, []);
  useEffect(() => {
    const frame = frameRef.current;
    if (fade !== "rows" || !frame) return;
    let gone = false;
    const measure = () => {
      const n = linesIn(frame);
      if (n !== undefined) setLines(n);
    };
    const resized = new ResizeObserver(measure);
    resized.observe(frame);
    const text = textIn(frame);
    if (text) resized.observe(text);
    document.fonts.ready.then(() => !gone && measure());
    return () => {
      gone = true;
      resized.disconnect();
    };
  }, [fade]);
  const estimate = Math.round((block.h - 2 * down) / rowMM);
  const mask = fade && Number.isFinite(rowMM) && rowMM > 0 && fadeMask(fade, lines ?? estimate, rowMM * k, (px) => `calc(var(--ink-up, 0px) + ${px}px)`);
  // A kind nobody knows draws as a rectangle, also one that names a part of every object ("toString").
  const d = Object.hasOwn(OUTLINES, p.kind ?? "") ? OUTLINES[p.kind!]?.(block.w, block.h, edge / 2, p) : undefined;
  // A browser lays a CSS border out on whole pixels: 0.5 mm printed as 0.26 mm. A shadow inside the box is as wide
  // as it is set, so that draws a solid border.
  const solid = !d && !p.dash && edge > 0;
  // Each browser draws the dashes of a CSS border its own way, so a box's dashes are drawn over it, as a line's are.
  // A box no larger than two strokes has no room for them, and keeps the border.
  const ring = !d && !!p.dash && edge > 0 && Math.min(block.w, block.h) > 2 * edge;
  // An outline is no border, so the padding alone keeps the text where a border would.
  const own = d || ring || solid ? 0 : edge;
  // Sheets saved before had a CSS border, which the print rounded down to whole pixels. The padding leaves the room
  // that border took, not the stroke's, so their texts keep their place and break their lines where they did.
  const room = ring || solid ? edge - Math.max(1, Math.floor(edge * k)) / k : own;
  // An inside shape's cut goes on its text (`--cut`, see styles.css), so the outline keeps its whole box.
  const frameCut = inside ? undefined : cut;
  const over: CSSProperties = { position: "absolute", inset: 0, width: "100%", height: "100%", zIndex: -1 };
  // The clip's four sides, top, right, bottom and left, as CSS inset values; a bubble's tail grows its side by the px it reaches out.
  const tops = tight ? `calc(-1px - ${above}em)` : "-1px";
  const rights = tight && side > 0 ? `calc(-1px - ${side}em)` : "-1px";
  const bottoms = frameCut !== undefined ? `calc(100% - ${frameCut}px)` : tight ? (below > 0 ? `calc(-1px - ${p.syllables ? ".3em - " : ""}${below}em)` : p.syllables ? "calc(-1px - .3em)" : "-1px") : p.syllables ? "calc(-1px - .3em)" : "-1px";
  const [tailUp, tailRight, tailDown, tailLeft] = tailReach(block).map((mm) => mm * k);
  const grow = (v: string, px: number) => (px > 0 ? `calc(${v} - ${px}px)` : v);
  const radius = p.kind === "circle" ? "50%" : p.kind === "rounded" ? `${radiusOf(p, block.w, block.h) * k}px` : 0;
  // A circle's clip grows by the side reach on each side, so its curve keeps the circle's radius as the box grows (#740).
  const roundR = p.kind === "circle" && side > 0 ? `calc(50% + ${side}em)` : radius;
  const text = (
    <>
      {children ??
        (linked && !paras.length ? (
          <div className="rich nolist" />
        ) : scramble ? (
          <Rich paras={paras} mix={mixed(paras, { seed: p.mix!, first: p.mixFirst === true, caps: p.mixCaps === true })} line={line} solved={solved} cols={cols} />
        ) : linked || p.rich ? (
          <Rich paras={paras} holes={holes} cols={cols} />
        ) : (
          <p>{p.text}</p>
        ))}
      {words.length > 0 && <Bank words={words} seed={p.bank!} />}
    </>
  );
  return (
    <div
      ref={frameRef}
      className={classes("frame", tints && "tinted", solved && "solved", width && "even", linked && "listed", tailed && "tailed", tight && "tight", inside && "inside")}
      data-trace={traceOf(p)}
      data-fade={fade}
      data-cut={cut !== undefined ? "true" : undefined}
      title={cut !== undefined ? "Text passt nicht ganz hinein" : undefined}
      style={{
        ...textStyle(p, k),
        ...(inside && { fontSize: `calc(${p.size * PT * k}px * var(--fit, 1))` }),
        ...(inside && cut !== undefined && { "--cut": `${cut}px` } as CSSProperties),
        ...(tight && { "--ink-up": level ? `calc(${above}em + ${fringe}px)` : "0px", "--ink-down": level ? `calc(${below}em + ${fringe}px)` : "0px", "--ink-side": side > 0 ? `calc(${side}em + 1px)` : "0px" }),
        ...gapVar(width, k),
        ...(mask && ({ "--fade": mask } as CSSProperties)),
        // A linked text grows to hold its words, past the height it is stored with.
        ...(linked && { height: "auto", minHeight: "100%" }),
        background: d ? undefined : clear(p),
        border: own ? `${edge * k}px ${p.dash} ${tint(p.stroke, p.strokeOpacity)}` : undefined,
        boxShadow: solid ? `inset 0 0 0 ${edge * k}px ${tint(p.stroke, p.strokeOpacity)}` : undefined,
        borderRadius: radius,
        // A pixel outside the box, so a stroke flush with its edge stays whole (see .frame in styles.css), and round
        // as the box, so a text too long for a circle ends at the circle. A bow under the last line hangs below a
        // box that is just as high as its text.
        clipPath: `inset(${grow(tops, tailUp)} ${grow(rights, tailRight)} ${grow(bottoms, frameCut !== undefined ? 0 : tailDown)} ${grow(rights, tailLeft)} round ${roundR})`,
        padding: `${(down - room + fitTop) * k}px ${(across - room + fitRight) * k}px ${(down - room + fitBottom) * k}px ${(across - room + fitLeft) * k}px`,
        ...(tailed
          ? { display: "grid", gridTemplateColumns: "minmax(0, 1fr)", gridTemplateRows: block.flipY ? "1fr 3fr" : "3fr 1fr", gridTemplateAreas: block.flipY ? '"." "words"' : '"words" "."' }
          : { justifyContent: UP[p.valign ?? "top"] }),
        ...((d || ring) && { position: "relative", isolation: "isolate" }),
      }}
    >
      {d && (
        // A linked text's outline goes with its frame when the words make that higher than the block.
        <svg className="outline" viewBox={`0 0 ${block.w} ${block.h}`} preserveAspectRatio={linked ? "none" : undefined} style={{ ...over, ...flipped(block) }}>
          {p.dash && edge > 0 ? (
            <Dashes way={POINTS[p.kind!]!(block.w, block.h, edge / 2, p)} edge={edge} p={p} fill={p.fill ?? "none"} fillOpacity={p.opacity ?? 1} />
          ) : (
            <Outline d={d} fill={p.fill ?? "none"} fillOpacity={p.opacity ?? 1} stroke={p.stroke ?? "none"} strokeOpacity={p.strokeOpacity} strokeWidth={p.strokeWidth ?? 0.5} strokeDasharray={dashes(p.dash, p.strokeWidth ?? 0.5)} strokeLinecap={p.dash === "dotted" ? "round" : undefined} strokeLinejoin="round" />
          )}
        </svg>
      )}
      {ring && (
        <svg className="dashes" viewBox={`0 0 ${block.w} ${block.h}`} style={over}>
          <Ring w={block.w - edge} h={block.h - edge} edge={edge} p={p} />
        </svg>
      )}
      {/* A bubble's text and its solution words stand in its body one under the other, as in any other frame. */}
      {tailed ? <div className="body" style={{ justifyContent: UP[p.valign ?? "top"] }}>{text}</div> : text}
      {(p.syllables || tints) && <Bows block={block} base={FONTS[fontOf(p.font)][2]} breaks={breaks} syllables={p.syllables} tints={tints} tintsAcross={p.tintsAcross} solved={solved} />}
    </div>
  );
}
