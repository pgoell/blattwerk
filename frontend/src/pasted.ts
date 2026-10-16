// Words pasted from another app, as the paragraphs and marks a text keeps. Parsed in an inert document: no script
// runs and no picture or link loads.
import type { List, Para, Run } from "./sheet";

type Marks = Omit<Run, "text">;

// What the editor cannot hold (pictures, scripts, styles, frames) drops with its words.
const SKIP = new Set(["SCRIPT", "STYLE", "NOSCRIPT", "TEMPLATE", "HEAD", "IMG", "SVG", "IFRAME", "OBJECT"]);
const BLOCK = new Set(["P", "DIV", "LI", "UL", "OL", "H1", "H2", "H3", "H4", "H5", "H6", "TR", "TD", "TH", "BLOCKQUOTE"]);

// A colour as #rrggbb, or nothing for a form the editor does not hold.
let canvas: CanvasRenderingContext2D | null | undefined;
function hex(v: string): string | undefined {
  const s = v.trim().toLowerCase();
  const short = /^#([0-9a-f])([0-9a-f])([0-9a-f])$/.exec(s);
  if (short) return "#" + short.slice(1).map((c) => c + c).join("");
  if (/^#[0-9a-f]{6}$/.test(s)) return s;
  const rgb = /^rgba?\(\s*(\d+)[,\s]+(\d+)[,\s]+(\d+)/.exec(s);
  if (rgb) return "#" + rgb.slice(1).map((n) => Math.min(255, +n).toString(16).padStart(2, "0")).join("");
  // A name such as red: the canvas gives it back as #rrggbb. A value it does not know keeps the marker.
  canvas ??= document.createElement("canvas").getContext("2d");
  if (!canvas) return undefined;
  canvas.fillStyle = "#000001";
  canvas.fillStyle = s;
  const got = String(canvas.fillStyle);
  return /^#[0-9a-f]{6}$/.test(got) && got !== "#000001" ? got : undefined;
}

// A Word list paragraph: its level (one to three in Word, nested two deep here) and whether its marker is a number.
function wordList(el: Element): { list: List; level: number } | undefined {
  const style = el.getAttribute("style") ?? "";
  const m = /mso-list:\s*l\d+\s+level(\d)/.exec(style);
  if (!m) return undefined;
  const marker = el.querySelector("span[style*='mso-list:Ignore' i]")?.textContent ?? "";
  const number = /^\s*\(?(\d+|[a-z]|[ivxlc]+)[.)]/i.test(marker);
  return { list: number ? "number" : "bullet", level: Math.min(2, Math.max(0, +m[1] - 1)) };
}

// The list a text stands in: its closest item, as a bullet or a number, nested two deep at most. A paragraph the
// editor's field copied carries its list in data-list and data-level.
function listOf(el: Element): { list?: List; level?: number } {
  const item = el.closest("li, p[data-list], p[style*='mso-list']");
  if (!item) return {};
  const word = wordList(item);
  if (word) return word;
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
    // Hidden text and Word's list markers, which the list shows instead, are no part of the words.
    if (SKIP.has(tag) || el.style.display === "none" || /mso-hide:\s*all/i.test(el.getAttribute("style") ?? "")) return;
    if (/mso-list:\s*ignore/i.test(el.getAttribute("style") ?? "")) return;
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
    const started = paras.length;
    el.childNodes.forEach((child) => walk(child, next));
    if (block) {
      brk();
      // A paragraph with no words is an empty line, as in the plain text. Word's own paragraph ends make no line of theirs.
      if (paras.length === started && /^(P|DIV|H[1-6]|BLOCKQUOTE)$/.test(tag)) paras.push({ runs: [] });
    }
  };
  walk(body, {});

  // Spaces at the ends of a paragraph go. Empty paragraphs keep their place between the words, not at the ends.
  for (const p of paras) {
    p.runs = p.runs.filter((r) => r.text);
    if (p.runs.length) {
      p.runs[0].text = p.runs[0].text.trimStart();
      p.runs[p.runs.length - 1].text = p.runs[p.runs.length - 1].text.trimEnd();
    }
    p.runs = p.runs.filter((r) => r.text);
  }
  const first = paras.findIndex((p) => p.runs.length);
  const last = paras.map((p) => p.runs.length > 0).lastIndexOf(true);
  return first < 0 ? [] : paras.slice(first, last + 1);
}
