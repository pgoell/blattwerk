// Letter colours painted over the text, without wrapping a letter in its own element: WebKit shapes
// each text node alone, which would break the joins of a school script. The same way the syllable
// colours are painted. A hand colour on a run keeps its letters. A gap's letters stay hidden.

import { useLayoutEffect, useRef } from "react";
import { inked, sane } from "../letters";
import { highlight, unmark, type Mark } from "./bows";

export { sane } from "../letters";

function handed(node: Text, p: Element) {
  for (let el = node.parentElement; el && el !== p; el = el.parentElement) if (el.style.color) return true;
  return false;
}

// The ranges of `host` that a mark colours. One paragraph at a time, so a word split over two runs
// is still one word. A gap is left alone unless the answer key is showing.
export function paint(host: HTMLElement, raw: unknown): Mark[] {
  const marks = sane(raw);
  const out: Mark[] = [];
  if (!marks) return out;
  const solved = !!host.closest(".solved");
  for (const p of host.querySelectorAll("p")) {
    if (p.querySelector("p")) continue;
    const nodes: Text[] = [];
    const walk = document.createTreeWalker(p, NodeFilter.SHOW_TEXT);
    while (walk.nextNode()) {
      const node = walk.currentNode as Text;
      if (node.parentElement?.closest("textarea")) continue;
      nodes.push(node);
    }
    if (!nodes.length) continue;
    const starts: number[] = [];
    let acc = 0;
    for (const node of nodes) {
      starts.push(acc);
      acc += node.data.length;
    }
    let at = 0;
    for (const part of inked(nodes.map((node) => node.data).join(""), marks)) {
      const from = at;
      at += part.text.length;
      if (!part.color) continue;
      const mark = highlight(part.color, "ink");
      if (!mark) continue;
      for (let i = 0; i < nodes.length; i++) {
        const nodeStart = starts[i];
        const lo = Math.max(from, nodeStart);
        const hi = Math.min(at, nodeStart + nodes[i].data.length);
        if (lo >= hi) continue;
        const node = nodes[i];
        if (handed(node, p) || (!solved && node.parentElement?.closest(".gap"))) continue;
        const range = document.createRange();
        range.setStart(node, lo - nodeStart);
        range.setEnd(node, hi - nodeStart);
        mark.add(range);
        out.push([mark, range]);
      }
    }
  }
  return out;
}

// The letter colours of the block this sits in. `unsplit` stands while they are not those of the
// text shown, so the PDF waits, as it does for the bows.
export function Inks({ marks }: { marks: unknown }) {
  const svg = useRef<SVGSVGElement>(null);
  const held = useRef<Mark[]>([]);
  const raw = useRef(marks);
  raw.current = marks;
  const draw = () => {
    const own = svg.current!;
    const old = held.current;
    held.current = paint(own.parentElement!, raw.current);
    unmark(old);
    own.classList.remove("unsplit");
  };
  useLayoutEffect(() => {
    const own = svg.current!;
    let frame = 0;
    const later = () => {
      own.classList.add("unsplit");
      frame ||= requestAnimationFrame(() => {
        frame = 0;
        draw();
      });
    };
    const changed = new MutationObserver((records) => records.some((record) => !own.contains(record.target)) && later());
    changed.observe(own.parentElement!, { characterData: true, childList: true, subtree: true });
    document.fonts.addEventListener("loadingdone", later);
    return () => {
      cancelAnimationFrame(frame);
      changed.disconnect();
      document.fonts.removeEventListener("loadingdone", later);
      unmark(held.current);
    };
  }, []);
  useLayoutEffect(() => {
    svg.current!.classList.add("unsplit");
    draw();
  }, [marks]);
  return <svg ref={svg} className="inks unsplit" aria-hidden />;
}
