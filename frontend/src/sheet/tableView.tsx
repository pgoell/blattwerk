// Draws a table.

import { cellEntries } from "../bank";
import { heightsOf, spansOf, rectOf } from "../cells";
import { edged, linesOf, type Pen } from "../edges";
import { pairOf, splitting, Bows } from "./bows";
import { useBreaks } from "./context";
import { keepsFractions, textStyle, fadeOf, fadeAt, traceOf, FONTS, fontOf } from "./look";
import { gapWidth, gapVar, classes, Bank } from "./shape";
import type { TableBlock } from "./table";
import { Scissors } from "lucide-react";
import { type ReactNode, useRef, useLayoutEffect, useState, type CSSProperties } from "react";

// The lines are the borders of the cells, so they close at every corner. The rows have no set height: the grid
// makes each as high as its cells need and stretches them all by the same share of what is left. A text lies in
// the middle of its cell's height. The editor passes the field for the cell `at`, counted row by row: the cell's
// own text, unseen, keeps the field as high as its lines.
export function Table({ block, k, at, reach, solved, children }: { block: TableBlock; k: number; at?: number; reach?: number; solved: boolean; children?: ReactNode }) {
  const { cells, cols, line, head, syllables, breaks: own, tintsAcross, gaps } = block.props;
  const breaks = useBreaks(own);
  const tints = pairOf(block.props.tints);
  const width = gapWidth(block.props.gapWidth);
  const words = typeof block.props.bank === "number" && Number.isFinite(block.props.bank) ? cellEntries(cells, gaps) : [];
  const heights = heightsOf(block.props);
  // A table with one of the new keys draws its lines in svgs laid over the cells, so the borders of the cells go
  // transparent: they keep their pixel in the layout and only the ink goes. An old table gets none of this.
  const styled = edged(block.props);
  const lineAt = linesOf(block.props);
  const plain = linesOf({ ...block.props, edges: undefined })("v", 0, 0);
  // One line of the grid, from one end to the other. A dashed or dotted line is drawn from each end to its middle,
  // so that the dashes start fresh at both ends and every corner gets a piece of dash from each side.
  const rim = (side: string, pen: Pen, [a, b, mid]: string[][]) => {
    if (pen.style === "none") return null;
    const w = pen.width * k;
    const pieces = pen.style === "solid" ? [[a, b]] : [[a, mid], [b, mid]];
    const dashes = pen.style === "dashed" ? { strokeDasharray: `${3 * w} ${4 * w}`, strokeDashoffset: 1.5 * w } : pen.style === "dotted" ? { strokeDasharray: `0 ${2.5 * w}` } : {};
    // The period of the dashes, which `fit` changes so that a whole number of them lies on the edge.
    const period = pen.style === "dashed" ? 7 * w : pen.style === "dotted" ? 2.5 * w : undefined;
    return pieces.map(([p, q], i) => (
      <line key={i} data-side={side} data-style={pen.style} data-period={period} data-w={w} x1={p[0]} y1={p[1]} x2={q[0]} y2={q[1]} stroke={line} strokeWidth={w} strokeLinecap={pen.style === "dotted" ? "round" : "square"} {...dashes} />
    ));
  };
  // Each dashed or dotted line gets a whole number of periods along its edge, so that the two halves meet in the
  // middle of a dash or a gap and no dash is doubled. It reads the sizes the layout already has, and does not change them.
  const host = useRef<HTMLDivElement>(null);
  const fit = (el: HTMLElement) => {
    const zoom = el.getBoundingClientRect().width / el.offsetWidth || 1;
    for (const svg of el.querySelectorAll<SVGSVGElement>(":scope > svg.edge")) {
      // Not clientWidth: that is whole pixels, and a column is seldom a whole number of them wide.
      const { width, height } = svg.getBoundingClientRect();
      const [across, down] = [width / zoom, height / zoom];
      // WebKit paints an svg from a whole pixel (measured: the floor, in CSS pixels), so its lines lie off by the rest.
      if (keepsFractions()) {
        const { left, top } = svg.getBoundingClientRect();
        const [dx, dy] = [left - Math.floor(left), top - Math.floor(top)].map((v) => v / zoom);
        svg.querySelector("g")!.setAttribute("transform", `translate(${-0.5 + dx} ${-0.5 + dy})`);
      }
      for (const line of svg.querySelectorAll<SVGLineElement>("line[data-period]")) {
        const side = line.dataset.side;
        const length = side === "top" || side === "bottom" ? across : down;
        if (!(length > 0)) continue;
        const period = Number(line.dataset.period);
        const w = Number(line.dataset.w);
        // A dot right at the end of its half is not drawn, by either half: so the dots are an odd number of
        // periods, and the middle of the edge lies between two of them.
        const n = length / period;
        const f = n / Math.max(1, line.dataset.style === "dotted" ? 2 * Math.round((n - 1) / 2) + 1 : Math.round(n));
        if (line.dataset.style === "dashed") {
          // An edge shorter than two of its line's widths has room for the caps of one dash and no more.
          const dash = Math.max(0, 4 * w * f - w);
          line.setAttribute("stroke-dasharray", `${dash} ${7 * w * f - dash}`);
          line.setAttribute("stroke-dashoffset", String(dash / 2));
        } else line.setAttribute("stroke-dasharray", `0 ${2.5 * w * f}`);
      }
    }
  };
  useLayoutEffect(() => {
    if (styled && host.current) fit(host.current);
  });
  // The sizes change when a font comes in or a row grows, and the fit follows them.
  useLayoutEffect(() => {
    const el = host.current;
    if (!styled || !el) return;
    const watch = new ResizeObserver(() => fit(el));
    watch.observe(el);
    el.querySelectorAll(":scope > svg.edge").forEach((svg) => watch.observe(svg));
    // The page that prints waits for the fonts and no longer: the fit is asked for before it, so it runs first.
    document.fonts.ready.then(() => fit(el));
    return () => watch.disconnect();
  }, [styled, cells.length, cols.length]);
  // A word too long for its closed cell breaks mid-letter. Such a cell gets soft hyphens at the syllable borders of its
  // broken words: they show as a hyphen only where the word breaks. The splitter loads only when a word breaks, and
  // the text it makes is kept until the cells or the breaks change.
  const key = `${cells.join("\u0001")}|${cols.join(",")}|${JSON.stringify(breaks ?? null)}`;
  const made = useRef<{ key: string; texts: Record<number, string>; done: Record<number, Set<string>>; pending: boolean }>({ key: "", texts: {}, done: {}, pending: false });
  const [, redraw] = useState(0);
  const mark = useRef<HTMLSpanElement>(null);
  useLayoutEffect(() => {
    const el = host.current;
    if (!el) return;
    const look = () => {
      const m = made.current;
      if (m.key !== key) Object.assign(m, { key, texts: {}, done: {}, pending: false });
      // A font still on its way draws wider letters: a word that fits would seem to break. The fonts that come in look again.
      if (document.fonts.status !== "loaded") return;
      const broken = new Map<number, Set<string>>();
      el.querySelectorAll<HTMLElement>(":scope > div[data-cell] > p:not(.open)").forEach((p) => {
        const cell = Number(p.parentElement!.dataset.cell);
        const walk = document.createTreeWalker(p, NodeFilter.SHOW_TEXT);
        for (let node = walk.nextNode() as Text | null; node; node = walk.nextNode() as Text | null) {
          for (const found of node.data.matchAll(/[\p{L}­]+/gu)) {
            const range = document.createRange();
            range.setStart(node, found.index!);
            range.setEnd(node, found.index! + found[0].length);
            // A word on two lines: its letters' tops lie a line apart, not a pixel.
            const tops = Array.from(range.getClientRects(), (r) => r.top);
            if (!tops.length || Math.max(...tops) - Math.min(...tops) < 3) continue;
            const words = broken.get(cell) ?? new Set<string>();
            words.add(found[0].replace(/­/g, ""));
            broken.set(cell, words);
          }
        }
      });
      // A word that breaks later in a cell already done (a bigger font, a narrower column) joins the cell's words.
      if (m.pending || [...broken].every(([c, words]) => [...words].every((w) => m.done[c]?.has(w)))) return;
      m.pending = true;
      // At once, not at the next render: the PDF looks for it in the next frame.
      mark.current?.classList.add("unsplit");
      redraw((n) => n + 1);
      splitting().then((module) => {
        if (m.key !== key) return;
        for (const [c, found] of broken) {
          const words = (m.done[c] = new Set([...(m.done[c] ?? []), ...found]));
          m.texts[c] = cells.flat()[c].replace(/\p{L}+/gu, (w) => {
            if (!words.has(w)) return w;
            let out = "";
            let last = 0;
            for (const place of module.cuts(w, breaks)) {
              out += w.slice(last, place) + "­";
              last = place;
            }
            return out + w.slice(last);
          });
        }
        m.pending = false;
        redraw((n) => n + 1);
        look();
      }, () => {
        // A splitter that does not load leaves the words as they break, and the print does not wait for it.
        m.pending = false;
        redraw((n) => n + 1);
      });
    };
    look();
    let gone = false;
    document.fonts.ready.then(() => gone || look());
    // A column that narrows inside a table of the same size changes no size of the table: its cells are watched too.
    const watch = new ResizeObserver(look);
    watch.observe(el);
    // And their texts: a bigger type in a cell held to its row's height grows only the text.
    el.querySelectorAll(":scope > div[data-cell], :scope > div[data-cell] > p").forEach((c) => watch.observe(c));
    document.fonts.addEventListener("loadingdone", look);
    return () => {
      gone = true;
      watch.disconnect();
      document.fonts.removeEventListener("loadingdone", look);
    };
    // A cell that closes draws its text anew, in a new paragraph: it is looked at and watched then.
  }, [key, at]);
  const hyphens = made.current.key === key ? made.current.texts : {};
  const pending = made.current.key === key && made.current.pending;
  // The marker set at once by hand follows the state after every render: a check dropped for new cells takes it away.
  useLayoutEffect(() => void mark.current?.classList.toggle("unsplit", made.current.key === key && made.current.pending));
  const TOP = [["0", "0"], ["100%", "0"], ["50%", "0"]];
  const BOTTOM = [["0", "100%"], ["100%", "100%"], ["50%", "100%"]];
  const LEFT = [["0", "0"], ["0", "100%"], ["0", "50%"]];
  const RIGHT = [["100%", "0"], ["100%", "100%"], ["100%", "50%"]];
  const style = {
    ...textStyle({ text: "", ...block.props }, k),
    borderColor: styled ? "transparent" : line,
    gridTemplateColumns: cols.map((c) => `minmax(0, ${c}fr)`).join(" "),
    ...(heights && { gridTemplateRows: heights.map((h) => `minmax(${h * k}px, auto)`).join(" ") }),
    "--edge": `${0.25 * k}px`,
    ...gapVar(width, k),
  };
  // A gap cell holds its text as a gap does; the open cell's field goes after it.
  const wrap = (text: string, i: number) => (gaps?.[Math.floor(i / cols.length)]?.[i % cols.length] === true ? <span className="gap" data-gap="true"><span>{text}</span></span> : text);
  // A trace text fades cell by cell: along the row for "row", from row to row for "rows". The lines stay solid.
  const fade = fadeOf(block.props);
  const shade = (i: number): CSSProperties | undefined =>
    fade && { opacity: fade === "row" ? fadeAt(i % cols.length, cols.length) : fadeAt(Math.floor(i / cols.length), cells.length) };
  // A merged cell is drawn once, over the cells it covers: those are not drawn, and each drawn cell takes its place in the grid.
  const spans = spansOf(block.props);
  const anchors = new Map(spans.map((s) => [s[0] * cols.length + s[1], s]));
  const covered = new Set(spans.flatMap(([r, c, h, w]) => Array.from({ length: h * w }, (_, n) => (r + Math.floor(n / w)) * cols.length + c + (n % w)).slice(1)));
  const place = (i: number) => spans.length > 0 && { gridRow: `${Math.floor(i / cols.length) + 1} / span ${anchors.get(i)?.[2] ?? 1}`, gridColumn: `${(i % cols.length) + 1} / span ${anchors.get(i)?.[3] ?? 1}` };
  // The cells of a selection of two or more are picked. The selection is whole, so a cell lies in it by its row and column.
  const area = at !== undefined && reach !== undefined ? rectOf(block.props, at, reach) : undefined;
  const picked = (i: number) => {
    if (!area || (area[2] - area[0] + 1) * (area[3] - area[1] + 1) < 2) return false;
    const r = Math.floor(i / cols.length);
    const c = i % cols.length;
    return r >= area[0] && r <= area[2] && c >= area[1] && c <= area[3];
  };
  return (
    <div ref={host} className={classes("table", tints && "tinted", solved && "solved", width && "even", styled && "edged")} data-trace={traceOf(block.props)} data-fade={fade} style={style as CSSProperties}>
      {cells.flat().map((text, i) => {
        const span = anchors.get(i);
        if (covered.has(i)) return null;
        return (
          <div key={i} data-cell={i} data-span={span && `${span[2]}x${span[3]}`} className={picked(i) ? "picked" : undefined} style={{ fontWeight: head && i < cols.length ? 700 : undefined, ...(place(i) || undefined) }}>
            {i === at ? <p className="open" style={shade(i)}>{wrap(text, i)}&#8203;{children}</p> : hyphens[i] !== undefined ? <p style={{ ...shade(i), hyphens: "manual", WebkitHyphens: "manual" }}>{wrap(hyphens[i], i)}</p> : <p style={shade(i)}>{wrap(text, i)}</p>}
          </div>
        );
      })}
      <span ref={mark} className={pending ? "unsplit" : undefined} hidden />
      {(syllables || tints) && <Bows block={block} base={FONTS[fontOf(block.props.font)][2]} breaks={breaks} syllables={syllables} tints={tints} tintsAcross={tintsAcross} solved={solved} />}
      {words.length > 0 && <Bank words={words} seed={block.props.bank!} />}
      {/* Each grid position: its top and left line, and at the rim the bottom and right ones. The scissors sit at the top left. */}
      {styled && cells.flatMap((_, r) => cols.map((_c, c) => (
        <svg key={`e${r}-${c}`} className="edge" data-edge={r * cols.length + c} style={{ gridRow: `${r + 1} / ${r + 2}`, gridColumn: `${c + 1} / ${c + 2}` }}>
          <g transform="translate(-0.5 -0.5)">
            {rim("top", lineAt("h", r, c), TOP)}
            {rim("left", lineAt("v", r, c), LEFT)}
            {r === cells.length - 1 && rim("bottom", lineAt("h", r + 1, c), BOTTOM)}
            {c === cols.length - 1 && rim("right", lineAt("v", r, c + 1), RIGHT)}
            {r === 0 && c === 0 && block.props.cut === true && (
              <g className="scissors">
                <Scissors size={4 * k} x={-4.5 * k} y={-2 * k} color={line} />
              </g>
            )}
          </g>
        </svg>
      )))}
      {/* The box of solution words takes the table's style on its left, right and bottom: its top is the table's bottom. */}
      {styled && words.length > 0 && (
        <svg className="edge" data-edge="bank" style={{ gridRow: `${cells.length + 1} / ${cells.length + 2}`, gridColumn: "1 / -1" }}>
          <g transform="translate(-0.5 -0.5)">
            {rim("left", plain, LEFT)}
            {rim("right", plain, RIGHT)}
            {rim("bottom", plain, BOTTOM)}
          </g>
        </svg>
      )}
    </div>
  );
}
