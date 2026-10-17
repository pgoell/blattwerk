import { flushSync } from "react-dom";
import { createRoot } from "react-dom/client";
import { Paper, type Block, type Doc } from "./sheet";

// Pixels per millimetre of the picture, the same whatever the zoom of the editor.
const PX = 4;
// Room round the blocks, in mm, so a border drawn on a block's edge is not cut in half.
const ROOM = 1;

// The box the blocks take on the sheet, in mm: a turned block takes the box of its turned corners.
function hullOf(blocks: Block[]) {
  const xs: number[] = [];
  const ys: number[] = [];
  for (const b of blocks) {
    const a = ((b.angle ?? 0) * Math.PI) / 180;
    const [cx, cy] = [b.x + b.w / 2, b.y + b.h / 2];
    const ex = (Math.abs(b.w * Math.cos(a)) + Math.abs(b.h * Math.sin(a))) / 2;
    const ey = (Math.abs(b.w * Math.sin(a)) + Math.abs(b.h * Math.cos(a))) / 2;
    xs.push(cx - ex, cx + ex);
    ys.push(cy - ey, cy + ey);
  }
  const [x, y] = [Math.min(...xs) - ROOM, Math.min(...ys) - ROOM];
  return { x, y, w: Math.max(...xs) + ROOM - x, h: Math.max(...ys) + ROOM - y };
}

// A style sheet's rules as text. One from another address may not be read, and the sheet needs none of those.
function rules(sheet: CSSStyleSheet) {
  try {
    return [...sheet.cssRules].map((r) => r.cssText).join("\n");
  } catch {
    return "";
  }
}

// A PNG of the blocks alone, cropped to where they lie, drawn as the sheet draws them on page `n`, whose size they keep.
export async function pictureOf(blocks: Block[], doc: Doc, n: number): Promise<Blob> {
  const { domToCanvas } = await import("modern-screenshot");
  // Drawn in a closed room of its own, with the page's styles, so nothing that looks for the sheet's blocks finds these.
  const host = document.createElement("div");
  host.style.cssText = "position:fixed;left:-100000px;top:0";
  const room = host.attachShadow({ mode: "closed" });
  const style = document.createElement("style");
  style.textContent = [...document.styleSheets].map(rules).join("\n");
  const box = document.createElement("div");
  room.append(style, box);
  document.body.append(host);
  const root = createRoot(box);
  try {
    // Only these blocks: no page number and none of the rest of the sheet.
    const alone = { ...doc, pages: [{ ...doc.pages[n], blocks }], pageNumbers: undefined };
    flushSync(() => root.render(<Paper doc={alone} k={PX} page={0} />));
    await document.fonts.ready;
    await Promise.all([...box.querySelectorAll("img")].map((img) => img.decode().catch(() => {})));
    const paper = await domToCanvas(box.querySelector<HTMLElement>(".paper")!);
    const h = hullOf(blocks);
    const out = document.createElement("canvas");
    out.width = Math.round(h.w * PX);
    out.height = Math.round(h.h * PX);
    out.getContext("2d")!.drawImage(paper, h.x * PX, h.y * PX, h.w * PX, h.h * PX, 0, 0, out.width, out.height);
    return await new Promise<Blob>((done, fail) => out.toBlob((blob) => (blob ? done(blob) : fail(new Error("no picture"))), "image/png"));
  } finally {
    root.unmount();
    host.remove();
  }
}
