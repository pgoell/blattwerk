// Syllable bows and syllable colours, measured where the letters already stand.

import type { Breaks } from "../syllables";
import { K, type Box } from "./box";
import type { Tints } from "./look";
import { useSyncExternalStore, useEffect, useRef, useLayoutEffect } from "react";

export type Splitter = typeof import("../syllables");
export let splitter: Splitter | undefined;
export let loading: Promise<Splitter> | undefined;
export const waiting = new Set<() => void>();
export const splitting = () =>
  (loading ??= import("../syllables").then(
    (module) => {
      splitter = module;
      waiting.forEach((tell) => tell());
      return module;
    },
    // A load that failed is tried again by the next block that asks.
    (failed) => {
      loading = undefined;
      throw failed;
    },
  ));
export const listen = (tell: () => void) => (waiting.add(tell), () => void waiting.delete(tell));
// The splitter once it is loaded, for a block with `on`; it loads at the first block that asks.
export function useSplitter(on?: boolean) {
  const module = useSyncExternalStore(listen, () => splitter);
  useEffect(() => void (on && splitting().catch(() => {})), [on]);
  return on ? module : undefined;
}
export const SVG = "http://www.w3.org/2000/svg";
// A sheet may come from anywhere: a pair is two colours of six hex digits, in lower case, and anything else is none.
export function pairOf(tints: unknown): Tints | undefined {
  if (!Array.isArray(tints) || tints.length !== 2) return undefined;
  const [a, b] = tints;
  const hex = (c: unknown): c is string => typeof c === "string" && /^#[0-9a-f]{6}$/i.test(c);
  return hex(a) && hex(b) ? [a.toLowerCase(), b.toLowerCase()] : undefined;
}
// Each colour is one highlight in the document's registry, named by the colour. Its rule goes into a style element
// the module makes at the first one. A browser without the registry paints no colours.
export let tinting: HTMLStyleElement | undefined;
export const rules = new Map<Highlight, [string, Text]>();
export function highlight(colour: string): Highlight | undefined {
  if (!("highlights" in CSS)) return undefined;
  const name = `tint-${colour.slice(1).toLowerCase()}`;
  let mark = CSS.highlights.get(name);
  if (!mark) {
    mark = new Highlight();
    CSS.highlights.set(name, mark);
    tinting ??= document.head.appendChild(document.createElement("style"));
    const rule = document.createTextNode(`::highlight(${name}){color:${colour}}`);
    tinting.append(rule);
    rules.set(mark, [name, rule]);
  }
  return mark;
}
// A range a block coloured, in the highlight it went into: the block takes it back before it draws anew. A colour
// that no letter has any more goes with its rule: a drag through the colour field passes hundreds of them.
type Mark = [Highlight, globalThis.Range];
export const unmark = (marks: Mark[]) =>
  marks.forEach(([mark, range]) => {
    mark.delete(range);
    const [name, rule] = rules.get(mark) ?? [];
    if (mark.size || !rule) return;
    CSS.highlights.delete(name!);
    rule.remove();
    rules.delete(mark);
  });
type Draw = { base: number; breaks?: Breaks; syllables?: boolean; tints?: Tints; tintsAcross?: boolean; solved?: boolean };
// Draws a bow under each syllable of the text beside `svg`: every paragraph of a frame, of a table's cells and of
// the field a text is typed in. The words stay as they are. A span around a syllable would move its letters:
// WebKit shapes each text node alone, which costs the joins and the kerning of a school script. So each syllable
// is measured where it stands and its bow drawn over it, in the block's own pixels: the zoom is divided out, and a
// turned block is measured level. The same pass colours the syllables in turn (Silbenfarbe) and returns the ranges
// it coloured, so a bow and its colour always fall on the same syllable.
export function bows(svg: SVGSVGElement, module: Splitter, { base, breaks, syllables, tints, tintsAcross: across }: Draw): Mark[] {
  const host = svg.parentElement!;
  const block = host.closest<HTMLElement>(".block");
  const turn = block?.style.transform;
  if (turn) block!.style.transform = "none";
  const { left, top } = svg.getBoundingClientRect();
  const scale = host.getBoundingClientRect().width / host.offsetWidth;
  const drawn: SVGPathElement[] = [];
  const marks: Mark[] = [];
  // The turn of the colours: `count` syllables so far, and the cell the last paragraph lay in.
  let cell: Element | null | undefined;
  let count = 0;
  // A table's open cell holds its text unseen around the field: the field's paragraphs are the ones to draw.
  for (const p of scale ? host.querySelectorAll("p") : [])
    if (!p.querySelector("p")) {
      // A paragraph starts the turn anew, unless the turn runs across the text: then only a new cell does.
      if (!across || p.closest("[data-cell]") !== cell) count = 0;
      cell = p.closest("[data-cell]");
      const nodes: Text[] = [];
      const walk = document.createTreeWalker(p, NodeFilter.SHOW_TEXT);
      // The field of a table's open cell holds the cell's text once more: its own letters are not the ones to count.
      while (walk.nextNode()) if (walk.currentNode.parentElement!.tagName !== "TEXTAREA") nodes.push(walk.currentNode as Text);
      // Where each text node starts in the paragraph's text: a word is split whole, whatever runs it lies in.
      const starts = nodes.map(((at) => (node) => (at += node.length) - node.length)(0));
      const spot = (at: number) => {
        const i = starts.filter((start) => start <= at).length - 1;
        return [nodes[i], at - starts[i]] as const;
      };
      // A text node is hand coloured when an element between it and the paragraph has a colour of its own.
      const handed = (node: Text) => {
        for (let el = node.parentElement; el && el !== p; el = el.parentElement) if (el.style.color) return true;
        return false;
      };
      let at = 0;
      let word: number | undefined;
      for (const piece of module.pieces(nodes.map((node) => node.data).join(""), breaks)) {
        const from = at;
        at += piece.text.length;
        if (!piece.syl) continue;
        if (piece.word !== word) {
          word = piece.word;
          if (!across) count = 0;
        }
        const [first, start] = spot(from);
        // The end lies in the node of the syllable's last letter, not at the start of the next.
        const [last, stop] = spot(from + module.shown(piece.text).length - 1);
        // A mixed word has no syllables: a syllable that starts or ends in its letters gets neither bow nor colour,
        // and the colours of the words after it go on as if it had none, in the key too.
        if (first.parentElement!.closest(".mixed") || last.parentElement!.closest(".mixed")) continue;
        const colour = tints?.[count++ % 2];
        // A gap shows neither bow nor colour, so the hidden letters stay hidden, a syllable that
        // starts or ends in a gap too; the answer key shows both.
        const hidden = first.parentElement!.closest(".gap") || last.parentElement!.closest(".gap");
        if (hidden && !host.closest(".solved")) continue;
        // A hand colour keeps its letters: each stretch of the syllable without one gets a range of its own.
        const mark = colour ? highlight(colour) : undefined;
        if (mark) {
          const stretch: globalThis.Range[] = [];
          let open: globalThis.Range | undefined;
          for (const node of nodes.slice(nodes.indexOf(first), nodes.indexOf(last) + 1)) {
            if (handed(node)) open = undefined;
            else {
              if (!open) {
                open = document.createRange();
                open.setStart(node, node === first ? start : 0);
                stretch.push(open);
              }
              open.setEnd(node, node === last ? stop + 1 : node.length);
            }
          }
          for (const part of stretch) {
            mark.add(part);
            marks.push([mark, part]);
          }
        }
        if (!syllables) continue;
        const range = document.createRange();
        range.setStart(first, start);
        range.setEnd(last, stop + 1);
        // A rect for each line the syllable stands in: one, unless a word too long for its line broke in it. A
        // syllable that two runs share has a rect for each run, side by side, and still one bow.
        const lines: { left: number; right: number; top: number; bottom: number }[] = [];
        // A word of a linked list that its row or its folded span cuts off gets no bow where it is hidden.
        const clipped = (x: number, y: number) => {
          for (let el: Element | null = first.parentElement; el && el !== host; el = el.parentElement) {
            if (!el.classList.contains("row") && (el as HTMLElement).style.overflow !== "hidden") continue;
            const box = el.getBoundingClientRect();
            if (x < box.left || x > box.right || y < box.top || y > box.bottom) return true;
          }
          return false;
        };
        for (const { left, right, top, bottom } of range.getClientRects()) {
          if (clipped((left + right) / 2, (top + bottom) / 2)) continue;
          const line = lines.find((line) => (top + bottom) / 2 > line.top && (top + bottom) / 2 < line.bottom);
          if (line) [line.left, line.right] = [Math.min(line.left, left), Math.max(line.right, right)];
          else if (right > left) lines.push({ left, right, top, bottom });
        }
        const look = getComputedStyle(first.parentElement!);
        const em = parseFloat(look.fontSize);
        for (const line of lines) {
          // The baseline lies `base` em below the middle of the letters' box, whatever the line spacing. The bow
          // ends .04em inside the syllable, so two bows never meet, .1em below the baseline, and hangs .16em
          // lower in its middle; under a narrow letter it is flatter.
          const [x, to] = [(line.left - left) / scale + 0.04 * em, (line.right - left) / scale - 0.04 * em];
          const y = ((line.top + line.bottom) / 2 - top) / scale + (base + 0.1) * em;
          const deep = Math.min(0.16 * em, (to - x) / 2);
          const path = document.createElementNS(SVG, "path");
          path.setAttribute("class", "syl");
          path.dataset.syl = module.plain(piece.text);
          // A curve hangs half as deep as the point it is drawn towards.
          path.setAttribute("d", `M${x.toFixed(2)},${y.toFixed(2)} Q${((x + to) / 2).toFixed(2)},${(y + 2 * deep).toFixed(2)} ${to.toFixed(2)},${y.toFixed(2)}`);
          // A bow takes the colour of its syllable, where the syllable's first letter has no hand colour of its own.
          path.setAttribute("stroke", colour && !handed(first) ? colour : look.color);
          // As thick as the letters ask, and never thinner than 0.15 mm, which still prints.
          path.setAttribute("stroke-width", `${Math.max(0.05 * em, 0.15 * K)}`);
          drawn.push(path);
        }
      }
    }
  if (turn) block!.style.transform = turn;
  svg.replaceChildren(...drawn);
  svg.classList.remove("unsplit");
  return marks;
}
// The bows of a block that asks for them. `base` is how far the font's baseline lies below the middle of a line,
// in em. They are measured anew only when something moved a letter or gave it another colour: `block` is the
// block as the sheet holds it, and a pick, or a letter typed into another block, leaves it the same. What React
// does not hold is watched: the text as the teacher types it, the block's size while it is dragged, and a font
// that comes in. `unsplit` stands while the bows are not those of the text shown, so the PDF, a test and a picture
// of the page can wait for them. It draws the bows when `syllables` is on, and the colours when there is a pair of
// `tints`; with the colours alone it draws no bow, and its ranges go when the block goes or its colours change.
export function Bows({ block, ...how }: { block: Box & { props: object } } & Draw) {
  const { solved } = how;
  const module = useSplitter(true);
  const svg = useRef<SVGSVGElement>(null);
  const tools = useRef({ draw: () => {}, seen: () => {}, drawn: () => {} });
  const size = useRef([0, 0]);
  const marks = useRef<Mark[]>([]);
  // With no splitter the block has no bows, and says it is done: a page prints without bows sooner than not at
  // all. A load that failed is asked for again here, at the next change of the block and not before, so a server
  // that is down is not asked with every frame. Chromium keeps a failed module for as long as the page lives and
  // asks no server again, so there the bows come with a reload.
  const draw = () => {
    const own = svg.current!;
    size.current = [own.parentElement!.offsetWidth, own.parentElement!.offsetHeight];
    // The old ranges go once the new ones are in: a colour that stays is never without a letter, and keeps its rule.
    const old = marks.current;
    marks.current = module ? bows(own, module, how) : [];
    unmark(old);
    if (!module)
      splitting().catch(() => {
        own.replaceChildren();
        own.classList.remove("unsplit");
      });
  };
  useLayoutEffect(() => {
    const own = svg.current!;
    let frame = 0;
    // One measure a frame, however much changed.
    const later = () => {
      own.classList.add("unsplit");
      frame ||= requestAnimationFrame(() => tools.current.draw());
    };
    // A size that React set is drawn for already.
    const resized = new ResizeObserver(() => (own.parentElement!.offsetWidth !== size.current[0] || own.parentElement!.offsetHeight !== size.current[1]) && later());
    resized.observe(own.parentElement!);
    // The bows drawn are a change too, and not one to draw anew for.
    const changed = new MutationObserver((records) => records.some((record) => !own.contains(record.target)) && later());
    changed.observe(own.parentElement!, { characterData: true, childList: true, subtree: true });
    // A shape that shrinks its text sets the share after the bows are drawn: a new share is drawn for again.
    let fit = own.parentElement!.style.getPropertyValue("--fit");
    const shrunk = new MutationObserver(() => {
      const now = own.parentElement!.style.getPropertyValue("--fit");
      if (now !== fit) later();
      fit = now;
    });
    shrunk.observe(own.parentElement!, { attributes: true, attributeFilter: ["style"] });
    document.fonts.addEventListener("loadingdone", later);
    // What React just wrote into the text is drawn for at once, so no frame shows old bows and none measures twice.
    tools.current.seen = () => {
      cancelAnimationFrame(frame);
      frame = 0;
      changed.takeRecords();
    };
    // WebKit sends no `loadingdone` for a font that was on its way at the draw, and the letters it moves keep the
    // bows of the font before (#960): until it is in, the bows are not yet those of the text, and say so.
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
      shrunk.disconnect();
      document.fonts.removeEventListener("loadingdone", later);
      unmark(marks.current);
    };
  }, []);
  useLayoutEffect(() => {
    tools.current.draw = () => {
      tools.current.seen();
      draw();
      tools.current.drawn();
    };
    svg.current!.classList.add("unsplit");
    tools.current.draw();
    // The place of a block moves no letter in it.
  }, [module, block.props, how.breaks, block.w, block.h, block.angle, solved]);
  return <svg ref={svg} className="bows unsplit" aria-hidden />;
}
// Resolves once every block's bows are drawn. The PDF waits for it.
export const bowed = () =>
  new Promise<void>((done) => {
    const look = () => (document.querySelector(".unsplit") ? requestAnimationFrame(look) : done());
    requestAnimationFrame(look);
  });
