// Words pasted from another app, as the paragraphs and marks a text keeps. Parsed in an inert document: no script
// runs and no picture or link loads.
import type { List, Para, Run } from "./sheet";

type Marks = Omit<Run, "text">;

// What the editor cannot hold (pictures, scripts, styles, frames) drops with its words.
const SKIP = new Set(["SCRIPT", "STYLE", "NOSCRIPT", "TEMPLATE", "HEAD", "IMG", "SVG", "IFRAME", "OBJECT"]);
const BLOCK = new Set(["P", "DIV", "LI", "UL", "OL", "H1", "H2", "H3", "H4", "H5", "H6", "TR", "BLOCKQUOTE"]);

// A colour as #rrggbb, or nothing for a form the editor does not hold.
function hex(v: string): string | undefined {
  const s = v.trim().toLowerCase();
  const short = /^#([0-9a-f])([0-9a-f])([0-9a-f])$/.exec(s);
  if (short) return "#" + short.slice(1).map((c) => c + c).join("");
  if (/^#[0-9a-f]{6}$/.test(s)) return s;
  const rgb = /^rgba?\(\s*(\d+)[,\s]+(\d+)[,\s]+(\d+)/.exec(s);
  if (rgb) return "#" + rgb.slice(1).map((n) => Math.min(255, +n).toString(16).padStart(2, "0")).join("");
  return undefined;
}

// The list a text stands in: its closest item, as a bullet or a number, nested two deep at most. A paragraph the
// editor's field copied carries its list in data-list and data-level.
function listOf(el: Element): { list?: List; level?: number } {
  const item = el.closest("li, p[data-list]");
  if (!item) return {};
  if (item.tagName === "P") {
    const list = (item as HTMLElement).dataset.list;
    const level = Math.min(2, +((item as HTMLElement).dataset.level ?? 0) || 0);
    return list === "bullet" || list === "number" ? { list, ...(level && { level }) } : {};
  }
  let depth = 0;
  for (let l: Element | null = item.closest("ul, ol"); l; l = l.parentElement?.closest("ul, ol") ?? null) depth++;
  const level = Math.min(2, Math.max(0, depth - 1));
  return { list: item.parentElement?.tagName === "OL" ? "number" : "bullet", ...(level && { level }) };
}

export function parasFromHtml(html: string): Para[] {
  const body = new DOMParser().parseFromString(html, "text/html").body;
  const paras: Para[] = [];
  let open = false;
  const brk = () => {
    open = false;
  };

  const text = (s: string, parent: Element, marks: Marks) => {
    let t = s.replace(/\s+/g, " ");
    if (!open) {
      if (!t.trim()) return;
      paras.push({ runs: [], ...listOf(parent) });
      open = true;
    }
    const runs = paras[paras.length - 1].runs;
    const prev = runs[runs.length - 1];
    if (prev && prev.text.endsWith(" ") && t.startsWith(" ")) t = t.slice(1);
    if (!t) return;
    const kept = Object.fromEntries(Object.entries(marks).filter(([, v]) => v)) as Marks;
    const look = (m: Marks) => [!!m.bold, !!m.italic, !!m.underline, m.color ?? ""].join();
    if (prev && look(prev) === look(kept)) prev.text += t;
    else runs.push({ text: t, ...kept });
  };

  const walk = (node: Node, marks: Marks) => {
    if (node.nodeType === Node.TEXT_NODE) return text(node.textContent ?? "", node.parentElement!, marks);
    if (node.nodeType !== Node.ELEMENT_NODE) return;
    const el = node as HTMLElement;
    const tag = el.tagName;
    if (SKIP.has(tag)) return;
    if (tag === "BR") return brk();
    const block = BLOCK.has(tag);
    // A mark the element sets wins over the one it inherits; what it does not set it keeps.
    const next: Marks = { ...marks };
    const fw = el.style.fontWeight;
    const w = fw === "normal" ? 400 : fw === "bold" || fw === "bolder" ? 700 : +fw;
    if (fw && !Number.isNaN(w)) next.bold = w >= 600;
    else if (/^(B|STRONG|H[1-6])$/.test(tag)) next.bold = true;
    const fs = el.style.fontStyle;
    if (fs) next.italic = fs === "italic" || fs === "oblique";
    else if (tag === "I" || tag === "EM") next.italic = true;
    if (/underline/.test(`${el.style.textDecoration} ${el.style.textDecorationLine}`) || tag === "U") next.underline = true;
    const colour = hex(el.style.color) ?? (tag === "FONT" ? hex(el.getAttribute("color") ?? "") : undefined);
    // Black is what the text has anyway: the block's own colour stays.
    if (colour && colour !== "#000000") next.color = colour;
    if (block) brk();
    el.childNodes.forEach((child) => walk(child, next));
    if (block) brk();
  };
  walk(body, {});

  // Spaces at the ends of a paragraph and empty paragraphs go.
  for (const p of paras) {
    p.runs = p.runs.filter((r) => r.text);
    if (p.runs.length) {
      p.runs[0].text = p.runs[0].text.trimStart();
      p.runs[p.runs.length - 1].text = p.runs[p.runs.length - 1].text.trimEnd();
    }
    p.runs = p.runs.filter((r) => r.text);
  }
  return paras.filter((p) => p.runs.length);
}
