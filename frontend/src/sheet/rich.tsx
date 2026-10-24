// Rich text: lists, gaps, mixed words and the line numbers beside a text.

import type { Part } from "../scramble";
import { SVG } from "./bows";
import { K } from "./box";
import { FONTS, fontOf, GREYS } from "./look";
import { stepOf, fromOf, classes } from "./shape";
import { type TextBlock, listColsOf, type Run, type Para } from "./text";
import { useRef, useLayoutEffect, type CSSProperties, Fragment } from "react";

// The numbers are 0.7 em of their text: small, so they stay out of the way of the text.
export const NUMBER_EM = 0.7;
// The line numbers of a text, beside `svg`, which is the block's own. The lines are counted as they break, over all
// the paragraphs of the text: an empty paragraph is no line. In columns the numbers count the rows of the grid.
// A number stands on every `step`th line that lies in the box; a line cut off below the box has none. Measured like
// the bows, in the block's own pixels.
export function numbering(svg: SVGSVGElement, block: TextBlock) {
  const host = svg.parentElement!.querySelector<HTMLElement>(":scope > .frame")!;
  const step = stepOf(block.props.lines);
  const turn = svg.parentElement!.style.transform;
  svg.parentElement!.style.transform = "none";
  const { left, top } = svg.getBoundingClientRect();
  const box = host.getBoundingClientRect();
  const scale = box.width / host.offsetWidth;
  const em = parseFloat(getComputedStyle(host).fontSize);
  // Half the height of a line, on the screen.
  const near = (parseFloat(getComputedStyle(host).lineHeight) * scale) / 2;
  const base = FONTS[fontOf(block.props.font)][2];
  const shown: SVGTextElement[] = [];
  let count = fromOf(block.props.linesFrom) - 1;
  // The rows not yet numbered. In columns the words of all paragraphs make one grid, so their rows are numbered
  // together, top to bottom; otherwise each paragraph is numbered as it comes.
  let rows: { top: number; bottom: number }[] = [];
  const columns = block.props.list === true && listColsOf(block.props) > 1;
  const number = () => {
    rows.sort((a, b) => a.top - b.top);
    for (const row of rows) {
      count++;
      const middle = (row.top + row.bottom) / 2;
      if (count % step || middle <= box.top || middle >= box.bottom) continue;
      const text = document.createElementNS(SVG, "text");
      text.setAttribute("class", "ln");
      text.dataset.line = String(count);
      text.setAttribute("text-anchor", "end");
      // Two mm left of the box, which is laid out at K pixels a mm.
      text.setAttribute("x", `${-2 * K}`);
      text.setAttribute("y", `${((middle - top) / scale + base * em).toFixed(2)}`);
      text.setAttribute("font-size", `${(NUMBER_EM * em).toFixed(2)}`);
      text.setAttribute("font-family", "Andika");
      text.setAttribute("fill", GREYS[1]);
      text.textContent = String(count);
      shown.push(text);
    }
    rows = [];
  };
  for (const p of scale ? host.querySelectorAll("p") : [])
    if (!p.querySelector("p")) {
      const nodes: Text[] = [];
      const walk = document.createTreeWalker(p, NodeFilter.SHOW_TEXT);
      // The line under a scrambled word is no line of the text: its word lies in the column under the mixed one.
      while (walk.nextNode()) {
        const el = walk.currentNode.parentElement!;
        if (el.tagName !== "TEXTAREA" && !el.closest(".mix.under .gap")) nodes.push(walk.currentNode as Text);
      }
      // A line is a row of rects that the text's words lie in. Spaces are no words: a line of spaces alone is as
      // empty as one with nothing, in a paragraph or between two line breaks. Two words stand in one line when
      // their tops are less than half a line apart: the box of a school script's letters is two lines high and
      // more, in WebKit above all, so it reaches over its neighbours.
      const range = document.createRange();
      for (const node of nodes)
        for (const word of node.data.matchAll(/\S+/g)) {
          range.setStart(node, word.index);
          range.setEnd(node, word.index + word[0].length);
          for (const rect of range.getClientRects()) if (rect.right > rect.left && !rows.some((row) => Math.abs(rect.top - row.top) < near)) rows.push({ top: rect.top, bottom: rect.bottom });
        }
      if (!columns) number();
    }
  if (columns) number();
  svg.parentElement!.style.transform = turn;
  svg.replaceChildren(...shown);
  svg.classList.remove("unsplit");
}
// A change inside the bows is no change of the letters: the bows are redrawn inside the frame and move none.
export const inBows = (node: Node) => (node instanceof Element ? node : node.parentElement)?.closest(".bows");
// The line numbers of a text that asks for them, drawn beside its box as the bows are. `unsplit` stands while they
// are not those of the text shown, so the PDF waits for them.
export function Numbers({ block }: { block: TextBlock }) {
  const svg = useRef<SVGSVGElement>(null);
  const tools = useRef({ draw: () => {}, seen: () => {}, drawn: () => {} });
  useLayoutEffect(() => {
    const own = svg.current!;
    const host = own.parentElement!.querySelector<HTMLElement>(":scope > .frame")!;
    let frame = 0;
    // One measure a frame, however much changed.
    const later = () => {
      own.classList.add("unsplit");
      frame ||= requestAnimationFrame(() => tools.current.draw());
    };
    // The frame and what lies in it: a font that comes in breaks the lines anew and makes the text higher or
    // lower, in a frame that stays as it is. WebKit sends no event for such a font.
    // A size the numbers are drawn for already is no news: an element says its size once when it is first watched.
    const sizes = new Map<Element, string>();
    const span = (el: Element) => `${(el as HTMLElement).offsetWidth} ${(el as HTMLElement).offsetHeight}`;
    const resized = new ResizeObserver((entries) => entries.some(({ target }) => sizes.get(target) !== span(target)) && later());
    const changed = new MutationObserver((records) => records.some((record) => !inBows(record.target)) && later());
    changed.observe(host, { characterData: true, childList: true, subtree: true });
    document.fonts.addEventListener("loadingdone", later);
    // What React just wrote into the text is drawn for at once, so no frame shows old numbers and none measures
    // twice. The text may lie in a new element since: that one is watched from now on.
    tools.current.seen = () => {
      cancelAnimationFrame(frame);
      frame = 0;
      changed.takeRecords();
      sizes.clear();
      for (const el of [host, ...host.children]) {
        sizes.set(el, span(el));
        resized.observe(el);
      }
    };
    // A font still on its way breaks the lines anew when it comes in: until then the numbers are not yet those
    // of the text, and say so.
    let gone = false;
    tools.current.drawn = () => {
      if (document.fonts.status !== "loading") return;
      own.classList.add("unsplit");
      document.fonts.ready.then(() => gone || later());
    };
    return () => {
      gone = true;
      cancelAnimationFrame(frame);
      resized.disconnect();
      changed.disconnect();
      document.fonts.removeEventListener("loadingdone", later);
    };
  }, []);
  useLayoutEffect(() => {
    tools.current.draw = () => {
      tools.current.seen();
      numbering(svg.current!, block);
      tools.current.drawn();
    };
    svg.current!.classList.add("unsplit");
    tools.current.draw();
  }, [block.props, block.w, block.h, block.angle]);
  return <svg ref={svg} className="numbers unsplit" aria-hidden />;
}

// The runs of a paragraph in groups: consecutive gap runs share one group, every other run has one of its own. With
// `single` every run has a group of its own, so each hidden letter of Lückenwörter is a gap of its own.
export const runGroups = (runs: Run[], single = false) =>
  runs.reduce<Run[][]>((all, r) => {
    const last = all.at(-1);
    if (!single && r.gap === true && last?.[0].gap === true) last.push(r);
    else all.push([r]);
    return all;
  }, []);

// A word in a sentence that is wider than its paragraph breaks at the block's edge, as a lone word does: the class
// `wide` lets it (`.mix.wide` in styles.css). The sizes are read in layout px (offsetWidth, clientWidth), which neither
// a turn of the block nor the editor's zoom changes. Every word's class is taken off first, so each is measured in the
// same state and the class does not flip back and forth.
export function markWide(root: HTMLElement) {
  const mixes = [...root.querySelectorAll<HTMLElement>(".mix")];
  mixes.forEach((mix) => mix.classList.remove("wide"));
  const wide = mixes.map((mix) => {
    const p = mix.closest("p")!;
    const style = getComputedStyle(p);
    const room = p.clientWidth - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight);
    return mix.offsetWidth > room;
  });
  mixes.forEach((mix, i) => mix.classList.toggle("wide", wide[i]));
}

// A text's paragraphs, in the markup the editor's field makes of them, so one stylesheet draws both. What a sheet
// stores is drawn as text alone, never as markup of its own. `mix` holds the parts of each paragraph in place of its
// runs (see `mixed`): a part with a `source` is one scrambled word, the others are runs as they are. `holes` marks
// Lückenwörter, and `cols` sets a linked text's words in that many columns, filled column by column.
export function Rich({ paras, mix, line, solved, holes, cols }: { paras: Para[]; mix?: Part[][]; line?: "after" | "under"; solved?: boolean; holes?: boolean; cols?: number }) {
  const root = useRef<HTMLDivElement>(null);
  // Measured after every render: the class is set again whenever React has written the paragraphs anew.
  useLayoutEffect(() => {
    if (root.current) markWide(root.current);
  });
  // Again when the block's size changes, and when the fonts are in: a font changes the widths, not the block's size.
  // Registered in a layout effect, which runs before Print's effect waits for the fonts, so the PDF is printed after it.
  useLayoutEffect(() => {
    const el = root.current;
    if (!el) return;
    const observer = new ResizeObserver(() => markWide(el));
    observer.observe(el);
    document.fonts.ready.then(() => markWide(el));
    return () => observer.disconnect();
  }, []);
  const or = (set: boolean | undefined, on: string, off: string) => (set === undefined ? undefined : set ? on : off);
  const run = ({ text, bold, italic, underline, color }: Run, key: number) => (
    <span key={key} style={{ fontWeight: or(bold, "700", "400"), fontStyle: or(italic, "italic", "normal"), textDecoration: underline ? "underline" : undefined, color }}>
      {text}
    </span>
  );
  // Consecutive gap runs make one gap: its outer span draws the line, its inner one holds the words.
  const gaps = (runs: Run[]) =>
    runGroups(runs, holes).map((group, g) =>
      group[0].gap === true ? (
        <span key={g} className="gap" data-gap="true">
          <span>{group.map((r, j) => run(r, j))}</span>
        </span>
      ) : (
        run(group[0], g)
      ),
    );
  // A scrambled word: the mixed letters, or the word as typed where the key shows it in their place, and a line for
  // the word as typed, after or under the mixed one.
  const scrambled = (source: string, runs: Run[], j: number) => (
    <span key={j} className={classes("mix", line === "under" && "under")} data-mix={source}>
      {solved && !line ? <span className="mixkey">{source}</span> : <span className="mixed">{runs.map((r, k) => run(r, k))}</span>}
      {line && (
        <>
          {" "}
          <span className="gap line">
            <span>{source}</span>
            {/* Drawn, not a background: a browser lays a thin gradient paler on the screen than the print has it. */}
            <svg aria-hidden>
              <line y1="50%" x2="100%" y2="50%" />
            </svg>
          </span>
        </>
      )}
    </span>
  );
  const grid: CSSProperties | undefined =
    cols && cols > 1 ? { display: "grid", gridAutoFlow: "column", gridTemplateRows: `repeat(${Math.ceil(paras.length / cols)}, auto)`, gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))`, columnGap: "1em" } : undefined;
  // A paragraph whose one scrambled word stands alone, with nothing but spaces about it: that word breaks at the
  // block's edge, as a word in a column does (`.lone` in styles.css).
  const lone = (i: number) => {
    const parts = mix?.[i] ?? [];
    return parts.filter((part) => part.source !== undefined).length === 1 && parts.every((part) => part.source !== undefined || part.runs.every((r) => !r.text.trim()));
  };
  return (
    <div ref={root} className={classes("rich", holes && "holes")} style={grid}>
      {paras.map((para, i) => (
        <p key={i} className={lone(i) ? "lone" : undefined} data-list={para.list} data-level={para.level || undefined}>
          {mix
            ? mix[i].map((part, j) => <Fragment key={j}>{part.source !== undefined ? scrambled(part.source, part.runs, j) : gaps(part.runs)}</Fragment>)
            : gaps(para.runs)}
          {/* A paragraph with no text is still a line high. */}
          {!para.runs.length && <br />}
        </p>
      ))}
    </div>
  );
}
