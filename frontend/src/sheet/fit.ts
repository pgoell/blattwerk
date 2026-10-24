// Shrinks a shape's type until its lines fit the box.

// The element of a frame that holds its text.
export const TEXT_IN = ":scope > p, :scope > .body > p, :scope > .rich, :scope > .body > .rich";
export const textIn = (frame: HTMLElement) => frame.querySelector<HTMLElement>(TEXT_IN) ?? undefined;
// The lines a frame's text has: its height past the padding, over its line height. Scrolled height, so a text too long
// counts all its lines. Undefined until the text is drawn.
export function linesIn(frame: HTMLElement) {
  const text = textIn(frame);
  if (!text) return undefined;
  const style = getComputedStyle(text);
  const line = parseFloat(style.lineHeight);
  if (!(line > 0)) return undefined;
  const n = Math.round((text.scrollHeight - parseFloat(style.paddingTop) - parseFloat(style.paddingBottom)) / line);
  return Number.isFinite(n) && n > 0 ? n : undefined;
}
// The smallest type a shape shrinks its text to, in pt: a child still reads it. A text set smaller keeps its size.
export const LEAST = 10;
// The share of a text's size it may shrink to.
export const leastOf = (size: number) => Math.min(1, LEAST / size) || 1;
// Shrinks a frame's type (`--fit`) until its lines fit its height and no word runs past its width, down to the share
// `least`. Each round measures the type it has and takes the share it is too big by. Up to three rounds: a line of a
// pixel does not shrink. Gives what the lines still reach past the room at the smallest type, in px: the editor grows
// the shape by it, as it grows a rectangle. `high` is the shape's height in px: a frame being written in is as high
// as its text.
export function fitText(el: HTMLElement, least: number, high: number, floor: boolean) {
  el.style.removeProperty("--fit");
  // A turned block lies level for the measure, so its lines run across.
  const block = el.parentElement!;
  const was = block.style.transform;
  block.style.transform = "none";
  // The room inside the padding: a text past its foot is no scroll of the frame, so the lines are measured.
  const box = el.getBoundingClientRect();
  const pad = getComputedStyle(el);
  // The desk's zoom: the screen measures in its px, the frame's sizes are in its own.
  const zoom = box.width / el.offsetWidth || 1;
  const [top, bottom] = [box.top + parseFloat(pad.paddingTop) * zoom, box.top + (high - parseFloat(pad.paddingBottom)) * zoom];
  // Too small to measure: a text is cut and the editor warns, but there is no lack to grow the shape by.
  if (bottom - top < 3) {
    block.style.transform = was;
    return { down: 0, across: 1, cut: !!el.textContent?.trim() };
  }
  // A paragraph is no taller than its frame, so its lines are measured where they lie, past its foot.
  const lowest = () =>
    Math.max(
      ...[...el.querySelectorAll<HTMLElement>("p")].map((p) => {
        const r = document.createRange();
        r.selectNodeContents(p);
        return Math.max(...[...r.getClientRects()].map((q) => lineFoot(q, p, zoom)));
      }),
    );
  // How much wider each paragraph's words are than its room, the padding at its sides (the ink's reach) left out.
  const widths = () =>
    [...el.querySelectorAll<HTMLElement>("p")].map((p) => {
      const s = getComputedStyle(p);
      const pad = parseFloat(s.paddingLeft) + parseFloat(s.paddingRight);
      return (p.scrollWidth - pad) / Math.max(1, p.clientWidth - pad);
    });
  let scale = 1;
  for (let round = 0; round < 3; round++) {
    const tall = (lowest() - top) / (bottom - top);
    const across = Math.max(...widths());
    // Too high or too wide: down to the smallest type. A floored shape's word too wide that the smallest type does not fit grows the shape.
    const side = across > 1.01 ? (floor ? Math.max(least, scale / across) : scale / across) : scale;
    const next = Math.min(side, tall > 1.01 ? Math.max(least, scale / tall) : scale);
    if (!(next < scale)) break;
    scale = next;
    el.style.setProperty("--fit", String(scale));
  }
  const past = (lowest() - bottom) / zoom;
  // The words still wider than the box at the smallest type: the shape grows by that share, as the frame's sides allow.
  const left = Math.max(...widths());
  // A word is cut where its line reaches past its paragraph's sides: the padding there holds the ink, and prints.
  const wide = [...el.querySelectorAll<HTMLElement>("p")].some((p) => {
    const r = document.createRange();
    r.selectNodeContents(p);
    const side = p.getBoundingClientRect();
    return [...r.getClientRects()].some((q) => q.right > side.right + zoom || q.left < side.left - zoom);
  });
  // A room no wider than the ink's padding gives nothing to grow by, across or down: the shape warns and keeps its size.
  const narrow = [...el.querySelectorAll<HTMLElement>("p")].some((p) => {
    const s = getComputedStyle(p);
    return p.clientWidth - parseFloat(s.paddingLeft) - parseFloat(s.paddingRight) < 1;
  });
  block.style.transform = was;
  return { down: past > 1 && !narrow ? past : 0, across: floor && left > 1.01 && !narrow ? left : 1, cut: past > 1 || wide };
}
// The bottom of a line's box, in px of the screen. A font's glyph box stands taller than its line, and the extra hangs
// half below the line, so that half is taken off the glyph box's foot.
export function lineFoot(q: DOMRect, p: HTMLElement, zoom: number) {
  const line = parseFloat(getComputedStyle(p).lineHeight) * zoom;
  return q.bottom - (line > 0 ? (q.height - line) / 2 : 0);
}
// The px from a frame's top where its lines end whole, when a line lies past the page's foot: the lowest line that
// lies wholly on the page. Measured level, as `fitText` measures it. Undefined when every line is on the page.
// An inside shape's cut is px from its text's top instead: its text is cut, not its outline (see `Frame`).
export function cutAt(el: HTMLElement) {
  const paper = el.closest<HTMLElement>(".paper, .sheet");
  // An inside shape's text stops at its inner box (its padding's foot), so it is measured even off the foot.
  const inside = el.classList.contains("inside");
  if (!paper && !inside) return undefined;
  // A frame well above the foot needs no measure: its box's lowest point (turned or not) and its overflow lie above it.
  const near = el.getBoundingClientRect();
  const scale = near.width / el.offsetWidth || 1;
  const reach = Math.max(0, el.scrollHeight - el.clientHeight) * scale;
  if (!inside && near.bottom + reach < paper!.getBoundingClientRect().bottom - 1) return undefined;
  const block = el.parentElement!;
  const was = block.style.transform;
  block.style.transform = "none";
  const box = el.getBoundingClientRect();
  const zoom = box.width / el.offsetWidth || 1;
  // The lowest px a line may reach: the page's foot, or the inner box's foot, whichever is higher.
  const onPage = paper ? (paper.getBoundingClientRect().bottom - box.top) / zoom : Infinity;
  const inner = inside ? el.clientHeight - parseFloat(getComputedStyle(el).paddingBottom) : Infinity;
  const foot = Math.min(onPage, inner);
  let whole = 0;
  let past = false;
  for (const p of el.querySelectorAll<HTMLElement>("p")) {
    const r = document.createRange();
    r.selectNodeContents(p);
    for (const q of r.getClientRects()) {
      if (q.width < 1 || q.height < 1) continue;
      const bottom = ((inside ? lineFoot(q, p, zoom) : q.bottom) - box.top) / zoom;
      // A line that fits is kept to the foot of its glyphs, so no tail of a g is cut.
      if (bottom <= foot + 0.5) whole = Math.max(whole, (q.bottom - box.top) / zoom);
      else past = true;
    }
  }
  const text = textIn(el);
  const from = inside && text ? (text.getBoundingClientRect().top - box.top) / zoom : 0;
  block.style.transform = was;
  return past ? whole - from : undefined;
}
