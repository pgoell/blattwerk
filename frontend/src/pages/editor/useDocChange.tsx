// One undo step: a change to the document, and the page's ground.
import type { PointerEvent } from "react";
import { api, type Refusal } from "../../api";
import { changed } from "../../history";
import { attempt } from "../../fault";
import { signed } from "../../saves";
import { sizeOf, type Doc, type Page } from "../../sheet";
import { made } from "../../zahlenmauer";
import { GROUND_HINT, SCALE_MAX, SCALE_MIN, paint as paintGround, trim as trimGround, turnedCut, type Ground } from "../../ground";
import { totals } from "../../totals";
import { next } from "../../cells";
import { round } from "./palette";
import { usePointers } from "./usePointers";

export function useDocChange(session: ReturnType<typeof usePointers>) {
  const file = session.file;
  const live = session.live;
  const setHist = session.setHist;
  const at = session.at;
  const setAt = session.setAt;
  const setChosen = session.setChosen;
  const rest = session.rest;
  const sheet = session.sheet;
  const setShaping = session.setShaping;
  const setTrimming = session.setTrimming;
  const pdfAsk = session.pdfAsk;
  const setPdfAsk = session.setPdfAsk;
  const groundHold = session.groundHold;
  const mergeKey = session.mergeKey;
  const ahead = session.ahead;
  const tight = session.tight;
  const sink = session.sink;
  const hold = session.hold;
  const pages = session.pages;
  const page = session.page;
  const blocks = session.blocks;
  const k = session.k;
  const from = session.from;
  const latest = session.latest;
  const upload = (...a: any[]) => (session as Record<string, any>).upload(...a);
  const cut = (...a: any[]) => (session as Record<string, any>).cut(...a);
  const edge = (...a: any[]) => (session as Record<string, any>).edge(...a);
  const scale = (...a: any[]) => (session as Record<string, any>).scale(...a);
  const pdf = (...a: any[]) => (session as Record<string, any>).pdf(...a);
  const calm = (...a: any[]) => (session as Record<string, any>).calm(...a);
// Changes that share a key within one gesture (a drag, typing, a colour picker) make one undo step.
  // `to` is the page in use after the change, and `from` the one before: read as last drawn, for a block from the
  // server comes after the drawing that asked for it.
  // A change that leaves the sheet as it is, as a second press on "Seitenbreite", is none, as in PowerPoint: no undo
  // step, redo stays, and the sheet stays saved. So it is with a gesture that ends where it began.
  function update(fn: (doc: Doc) => Doc, key = "", to = page, from = latest.current.page) {
    const next = changed(live.current, { key: mergeKey.current, ahead: ahead.current }, totals(live.current.doc, fn(live.current.doc)), key, from, to);
    if (!next) {
      // A gesture under way goes on, and what it has changed is measured where its end asks for that, as a resize's.
      if (key !== "" && key === mergeKey.current) return void (tight.current && setHist((h) => ({ ...h })));
      // Any other gesture is over: the next change is a step of its own. No text has grown, so nothing is measured,
      // unless a change still waits to be drawn.
      mergeKey.current = "";
      if (live.current.doc === latest.current.doc) tight.current = sink.current = false;
      return;
    }
    ahead.current = next.gesture.ahead;
    mergeKey.current = next.gesture.key;
    // `setHist` hands its step the history as it stands, and that is what `changed` was given.
    setHist(() => next.h);
  }
  // Changes one page, the one in use unless `n` names another. Undo and redo of it show that page.
  function turn(fn: (p: Page) => Page, key?: string, n = page) {
    update((doc) => ({ ...doc, pages: doc.pages.map((p, i) => (i === n ? fn(p) : p)) }), key, n, n);
  }
  // The page without its ground, or with `ground` in its place.
  function withGround(p: Page, ground: Ground | undefined): Page {
    if (!ground) {
      const { ground: _gone, ...rest } = p;
      return rest;
    }
    return { ...p, ground };
  }
  function oneGround(item: { id: number; width: number; height: number }, n: number) {
    const ground: Ground = { upload: item.id, ratio: item.width / item.height, cut: [0, 0, 0, 0] };
    turn((p) => withGround(p, ground), "", n);
    setAt(n);
    setShaping(false);
    setTrimming(false);
    setPdfAsk(undefined);
  }
  // Each PDF page becomes the ground of one sheet page, from `from` on. Pages are added when the PDF has more.
  function manyGrounds(made: { id: number; width: number; height: number }[], from: number) {
    update((doc) => {
      const pages = doc.pages.slice();
      const lie = doc.pages[from]?.landscape;
      made.forEach((item, i) => {
        const ground: Ground = { upload: item.id, ratio: item.width / item.height, cut: [0, 0, 0, 0] };
        const n = from + i;
        if (pages[n]) pages[n] = { ...pages[n], ground };
        else pages.push({ blocks: [], ground, ...(lie !== undefined ? { landscape: lie } : {}) });
      });
      return { ...doc, pages };
    }, "", from);
    setAt(from);
    setChosen([from]);
    setShaping(false);
    setTrimming(false);
    setPdfAsk(undefined);
  }
  function fadeGround(opacity: number) {
    turn((p) => (p.ground && (p.ground.opacity ?? 1) !== opacity ? { ...p, ground: { ...p.ground, opacity } } : p));
  }
  function turnGround() {
    turn((p) => (p.ground ? { ...p, ground: { ...p.ground, turns: ((p.ground.turns ?? 0) + 1) % 4, cut: turnedCut(p.ground.cut) } } : p));
  }
  function clearGround() {
    turn((p) => withGround(p, undefined));
    setShaping(false);
    setTrimming(false);
  }
  function beginGround(e: PointerEvent<HTMLElement>, kind: "move" | "scale" | "trim", edge?: number) {
    const g = live.current.doc.pages[page].ground;
    if (!g || e.button) return;
    e.stopPropagation();
    e.preventDefault();
    const [w, h] = sizeOf(live.current.doc, page);
    const box = paintGround(w, h, g);
    const rect = sheet.current?.getBoundingClientRect();
    let dist: number | undefined;
    if (kind === "scale" && rect) {
      dist = Math.hypot((e.clientX - rect.left) / k - (box.x + box.width / 2), (e.clientY - rect.top) / k - (box.y + box.height / 2));
    }
    e.currentTarget.setPointerCapture(e.pointerId);
    groundHold.current = { kind, x: e.clientX, y: e.clientY, ground: g, edge, dist };
  }
  function dragGround(e: PointerEvent<HTMLElement>) {
    const hold = groundHold.current;
    if (!hold) return;
    const [w, h] = sizeOf(live.current.doc, page);
    const box = paintGround(w, h, hold.ground);
    if (hold.kind === "move") {
      const at: [number, number] = [round((hold.ground.at?.[0] ?? 0) + (e.clientX - hold.x) / k), round((hold.ground.at?.[1] ?? 0) + (e.clientY - hold.y) / k)];
      turn((p) => (p.ground ? { ...p, ground: { ...hold.ground, at } } : p), "ground");
      return;
    }
    if (hold.kind === "scale" && hold.dist && sheet.current) {
      const rect = sheet.current.getBoundingClientRect();
      const dist = Math.hypot((e.clientX - rect.left) / k - (box.x + box.width / 2), (e.clientY - rect.top) / k - (box.y + box.height / 2));
      const scale = Math.min(SCALE_MAX, Math.max(SCALE_MIN, round((hold.ground.scale ?? 1) * (dist / hold.dist))));
      turn((p) => (p.ground ? { ...p, ground: { ...hold.ground, scale } } : p), "ground");
      return;
    }
    if (hold.kind === "trim" && hold.edge !== undefined) {
      const [l, t, r, b] = hold.ground.cut;
      const cw = Math.max(0.05, 1 - (l || 0) - (r || 0));
      const ch = Math.max(0.05, 1 - (t || 0) - (b || 0));
      const along = hold.edge % 2 === 0 ? ((e.clientX - hold.x) / k / box.width) * cw : ((e.clientY - hold.y) / k / box.height) * ch;
      const cut = trimGround(hold.ground.cut, hold.edge, (hold.edge < 2 ? 1 : -1) * along);
      turn((p) => (p.ground ? { ...p, ground: { ...hold.ground, cut } } : p), "ground");
    }
  }
  function endGround() {
    groundHold.current = undefined;
  }
  const NO_GROUND = "Der Hintergrund konnte nicht hochgeladen werden.";
  function groundWhy(s: string, e: unknown) {
    const detail = (e as Refusal).detail;
    if (detail) return detail;
    if (s === "413" || s === "415" || s === "422") return GROUND_HINT;
    return undefined;
  }
  async function postGround(file: File, which?: string) {
    const body = new FormData();
    body.append("file", file);
    if (which !== undefined) body.append("which", which);
    return signed(api<{ pages: number; made: { page: number; id: number; width: number; height: number }[] }>("/grounds", { method: "POST", body }));
  }
  async function chooseGround(file: File) {
    setPdfAsk(undefined);
    await attempt(NO_GROUND, async () => {
      const pdf = file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
      const body = await postGround(file);
      const n = latest.current.page;
      if (!pdf || body.pages <= 1) {
        const item = body.made[0] ?? (await postGround(file, "1")).made[0];
        calm(() => oneGround(item, n));
        return;
      }
      setPdfAsk({ file, pages: body.pages, page: 1 });
    }, groundWhy);
  }
  async function takeAsked(which: string) {
    if (!pdfAsk) return;
    const file = pdfAsk.file;
    const n = latest.current.page;
    await attempt(NO_GROUND, async () => {
      const body = await postGround(file, which);
      calm(() => (which === "all" ? manyGrounds(body.made, n) : oneGround(body.made[0], n)));
    }, groundWhy);
  }
    return Object.assign(session, { update, turn, withGround, oneGround, manyGrounds, fadeGround, turnGround, clearGround, beginGround, dragGround, endGround, NO_GROUND, groundWhy, postGround, chooseGround, takeAsked });
}
