// New blocks, and pictures that land on the page.
import { useEffect, useRef } from "react";
import { api } from "../../api";
import { fresh } from "../../history";
import { attempt, status } from "../../fault";
import { signed } from "../../saves";
import { MARGIN, mathsHeight, read, sizeOf, type Block, type Doc } from "../../sheet";
import { pasted } from "../../words";
import { made } from "../../zahlenmauer";
import { copied } from "../../clip";
import { drawn } from "../Format";
import { generate, newSeed } from "../Maths";
import { MATHS, filled, type Fresh as Insert } from "../../insert";
import type { Breaks } from "../../syllables";
import type { Fresh } from "./palette";
import { round, TYPES, cloned } from "./palette";
import { usePageScroll } from "./usePageScroll";

export function useInsert(session: ReturnType<typeof usePageScroll>) {
  const file = session.file;
  const live = session.live;
  const setAt = session.setAt;
  const setIds = session.setIds;
  const rest = session.rest;
  const setEditing = session.setEditing;
  const words = session.words;
  const onPage = session.onPage;
  const side = session.side;
  const left = session.left;
  const desk = session.desk;
  const held = session.held;
  const away = session.away;
  const spot = session.spot;
  const pages = session.pages;
  const page = session.page;
  const blocks = session.blocks;
  const W = session.W;
  const H = session.H;
  const k = session.k;
  const from = session.from;
  const free = session.free;
  const boxes = session.boxes;
  const line = session.line;
  const keep = session.keep;
  const top = session.top;
  const still = session.still;
  const latest = session.latest;
  const update = session.update;
  const turn = session.turn;
  const seen = session.seen;
  const looked = session.looked;
  const mark = session.mark;
  const land = session.land;
  const calm = session.calm;
  const cut = (...a: any[]) => (session as Record<string, any>).cut(...a);
// The block lands on page `n` of the sheet as last drawn, and that page is in use from then on.
  // A block the teacher inserts goes under the lowest block of the page, at its left edge, when it fits above the
  // margin there. Words and pictures pasted from another app keep the place at the top of the view.
  // The first spot of page `p` where a w x h box keeps 5 mm from every block, scanned in rows from the top, in steps of 5 mm.
  function freeSpot(doc: Doc, p: number, w: number, h: number) {
    const [W, H] = sizeOf(doc, p);
    const boxes = filled(doc.pages[p].blocks);
    for (let y = MARGIN; y <= H - MARGIN - h; y += 5)
      for (let x = MARGIN; x <= W - MARGIN - w; x += 5)
        if (boxes.every((b) => x + w + 5 <= b.x || x >= b.x + b.w + 5 || y + h + 5 <= b.y || y >= b.y + b.h + 5)) return { p, x, y };
    return undefined;
  }
  function add(w: number, h: number, rest: Fresh, n = looked(), pasted = false) {
    const { doc } = latest.current;
    const [held, size] = [doc.pages[n].blocks, sizeOf(doc, n)];
    const id = crypto.randomUUID();
    // Under the lowest block of page p, at its left edge, when it fits above the margin there.
    const below = (p: number) => {
      const outer = filled(doc.pages[p].blocks);
      if (!outer.length) return undefined;
      const [W, H] = sizeOf(doc, p);
      const low = outer.reduce((a, b) => (b.y + b.h > a.y + a.h ? b : a));
      return low.y + low.h + 5 + h <= H - MARGIN ? { p, x: Math.max(0, Math.min(low.x, W - MARGIN - w)), y: round(low.y + low.h + 5) } : undefined;
    };
    // Under the lowest block, else the first free spot, on page n and then on each later page; else a new page after the last.
    const free = () => {
      for (let p = n; p < doc.pages.length; p++) {
        const spot = below(p) ?? freeSpot(doc, p, w, h);
        if (spot) return spot;
      }
      return { p: doc.pages.length, x: MARGIN, y: MARGIN };
    };
    const spot = pasted || !held.length ? { p: n, x: (size[0] - w) / 2, y: round(Math.max(0, seen(0, n))) + MARGIN } : free();
    const { p } = spot;
    const onPage = p < doc.pages.length;
    const z = Math.max(0, ...(onPage ? doc.pages[p].blocks : []).map((b) => b.z)) + 1;
    const [block] = land([{ id, x: spot.x, y: spot.y, w, h, z, locked: false, ...rest }], onPage ? doc.pages[p].blocks : [], onPage ? sizeOf(doc, p) : size);
    // A new page is one step with the block, and takes the format of page n.
    if (onPage) turn((q) => ({ ...q, blocks: [...q.blocks, block] }), undefined, p);
    else update((d) => ({ ...d, pages: [...d.pages, { blocks: [block], landscape: d.pages[n].landscape }] }), "", p);
    setAt(p);
    setIds([id]);
    // A block under the view is brought into it, once it is drawn.
    requestAnimationFrame(() => document.querySelector(`[data-id="${id}"]`)?.scrollIntoView({ block: "nearest", inline: "nearest" }));
    // An empty text opens for typing; a pasted one comes with its words.
    if (rest.type === "text" && !rest.props.text) setEditing(id);
  }
  // The picture as the server holds it, measured once it decodes.
  async function served(id: number) {
    const img = new Image();
    img.src = `/api/uploads/${id}`;
    await img.decode();
    return { width: img.naturalWidth, height: img.naturalHeight };
  }
  // A picture goes to the server first; the block holds its number and its shape, and starts within 100 mm.
  async function sent(file: File) {
    const body = new FormData();
    body.append("file", file);
    // What the server says counts before what the browser makes of the file: WebKit reads no file while it has no
    // connection, and the file is not the one to blame then.
    // Chromium cannot decode an SVG here: the server's cleaned copy is measured instead.
    const svg = file.type === "image/svg+xml";
    const drawn = svg ? null : createImageBitmap(file);
    drawn?.catch(() => {});
    const { id } = await signed(api<{ id: number }>("/uploads", { method: "POST", body }));
    const { width, height } = drawn ? await drawn : await served(id);
    const w = round(Math.min(100, (100 * width) / height));
    return { w, h: round((w * height) / width), type: "image" as const, props: { upload: id, ratio: width / height, cut: [0, 0, 0, 0] } };
  }
  // With no connection or a fault of the server the picture can be sent again. Any other refusal is the file's own:
  // one the server does not take, or one the browser cannot read.
  const NO_PICTURE = "Das Bild konnte nicht hochgeladen werden.";
  const unfit = (s: string) => (s === "offline" || s.startsWith("5") ? undefined : "Das Bild ließ sich nicht hochladen. Es gehen JPEG, PNG, WebP und GIF bis 15 MB, SVG bis 2 MB.");
  async function upload(file?: File, pasted = false) {
    if (!file) return;
    await attempt(
      NO_PICTURE,
      async () => {
        const where = mark();
        const { w, h, ...rest } = await sent(file);
        calm(() => add(w, h, rest, where(), pasted));
      },
      unfit,
    );
  }
  // Dropped files land with the first one's middle under the pointer, on the page that lies there, and each next one
  // 5 mm right and down. They stay where they were dropped, also on a block, so they only move as far as the page
  // needs to hold them. The page and the spot are read at once: the desk may scroll while the pictures are on their way.
  // The ones that did not arrive are sent again by the line's button, and land on the same spot.
  function dropped(files: File[], left: number, top: number) {
    // Beside the pages, the nearest one takes the drop.
    const rects = [...desk.current!.querySelectorAll<HTMLElement>("[data-page]")].map((el) => el.getBoundingClientRect());
    const away = rects.map((r) => Math.hypot(Math.max(r.left - left, 0, left - r.right), Math.max(r.top - top, 0, top - r.bottom)));
    const was = away.indexOf(Math.min(...away));
    const [x, y] = [(left - rects[was].left) / k, (top - rects[was].top) / k];
    let rest = files;
    return attempt(NO_PICTURE, () => landed(rest, was, x, y, (still) => void (rest = still)), unfit);
  }
  // A picture from a web page comes as its address: a data: address is read here, as a file, and a web address is not
  // fetched (a browser refuses it across sites, and the server must not ask it). A dragged link with no picture adds nothing.
  const WEB_PICTURE = "Ein Bild von einer Webseite lässt sich nicht hereinziehen. Kopiere es dort und füge es hier mit Strg+V ein, oder speichere es und ziehe die Datei herein.";
  function dropLink(data: DataTransfer, left: number, top: number) {
    const html = data.getData("text/html");
    const pic = html ? new DOMParser().parseFromString(html, "text/html").querySelector("img") : null;
    const img = pic?.getAttribute("src");
    const uri = data.getData("text/uri-list").split(/\r?\n/).find((line) => line && !line.startsWith("#"));
    // The address the browser hands over is the picture shown: a lazy picture's `src` may be a blank placeholder. A
    // picture in a link hands over the link's address instead: then its <img> tells.
    const address = uri?.startsWith("data:image/") || (uri && pic && !pic.closest("a[href]")) ? uri : (img ?? undefined);
    if (!address) return;
    const read = /^data:image\/(png|jpeg|gif|webp);base64,([A-Za-z0-9+/=]+)$/.exec(address);
    if (!read) return attempt(WEB_PICTURE, () => Promise.reject(), () => WEB_PICTURE);
    const [, kind, b64] = read;
    const bytes = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
    return dropped([new File([bytes], `bild.${kind}`, { type: `image/${kind}` })], left, top);
  }
  // Sends the files and lands those that arrived. Tells which did not, and throws why.
  async function landed(files: File[], was: number, x: number, y: number, keep: (still: File[]) => void) {
    const where = mark(was);
    const got = await Promise.allSettled(files.map((f) => (TYPES.includes(f.type) ? sent(f) : Promise.reject())));
    const made = got.flatMap((r) => (r.status === "fulfilled" ? [{ ...r.value, id: crypto.randomUUID() }] : []));
    if (made.length)
      calm(() => {
        // The pages may have changed while the pictures were on their way.
        const n = where();
        // The stack as a whole stays on the page, so its pictures keep their steps at an edge too.
        const [w, h] = sizeOf(latest.current.doc, n);
        const most = [w, h].map((side, axis) => side - Math.max(...made.map((b) => (axis ? b.h : b.w))) - 5 * (made.length - 1));
        const [cx, cy] = [x - made[0].w / 2, y - made[0].h / 2].map((c, axis) => Math.max(0, Math.min(c, most[axis])));
        // All of them are one undo step, on top of what the page holds by then.
        turn(
          (p) => {
            const z = Math.max(0, ...p.blocks.map((b) => b.z));
            const fresh = made.map((b, i) => ({
              ...b,
              x: round(Math.max(0, Math.min(cx + 5 * i, w - b.w))),
              y: round(Math.max(0, Math.min(cy + 5 * i, h - b.h))),
              z: z + 1 + i,
              locked: false,
            }));
            return { ...p, blocks: [...p.blocks, ...fresh] };
          },
          undefined,
          n,
        );
        setAt(n);
        setIds(made.map((b) => b.id));
      });
    keep(files.filter((_, i) => got[i].status === "rejected"));
    const why = got.flatMap((r) => (r.status === "rejected" ? [r.reason as Error | undefined] : []));
    // The session run out says nothing, and a picture that can be sent again counts before a file's own fault.
    if (why.length) throw why.find((e) => e?.message === "401") ?? why.find((e) => !unfit(status(e))) ?? why[0];
  }
  // What an insert button makes, from insert.ts.
  const addInsert = (f: Insert) => add(f.w, f.h, f);
  // A maths block starts with plus exercises up to 20; the server makes them.
  async function addMaths() {
    const limits = MATHS.limits(newSeed());
    await attempt("Die Aufgaben konnten nicht erzeugt werden.", async () => {
      const where = mark();
      const props = { ...limits, ...(await generate(limits)), ...MATHS.look };
      calm(() => add(MATHS.w, mathsHeight(props), { type: "maths", props }, where()));
    });
  }
  // `got` is the sheet's Lernwörter when the blocks bring a list the sheet lacks: it comes in the same step.
  function put(from: Block[], got?: string[]) {
    const copies = land(
      cloned([...from].sort((a, b) => a.z - b.z), blocks).map((b, i) => ({ ...b, z: top + 1 + i })),
    );
    update((doc) => ({ ...doc, ...(got && { words: got }), pages: doc.pages.map((p, i) => (i === page ? { ...p, blocks: [...p.blocks, ...copies] } : p)) }), "", page, page);
    setIds(copies.map((b) => b.id));
  }
  // The copied blocks lie in the browser's store: they last over a reload and reach another sheet and another tab.
  // They carry the account's id, for the browser may serve another account next.
  // Their words go to the system's clipboard, which pushes out a picture copied before: the newest copy wins.
  // They go out in a copy of the browser's own, which needs no leave and is done before the next paste. A copy with
  // no words waiting, as a field's, stays the browser's.
  const pending = useRef<string | null>(null);
  useEffect(() => {
    const copied = (e: ClipboardEvent) => {
      if (pending.current === null) return;
      e.clipboardData!.setData("text/plain", pending.current);
      pending.current = null;
      e.preventDefault();
      e.stopPropagation();
    };
    window.addEventListener("copy", copied, true);
    return () => window.removeEventListener("copy", copied, true);
  }, []);
  // A copy with no words still stamps the system's clipboard, with a blank.
  const wordsOf = (held: Block[]) => held.map((b) => ("text" in b.props && b.props.text) || "").filter(Boolean).join("\n") || " ";
  // The sheet's mends go along with the copied texts and tables, so a paste into another sheet keeps them. A block's own entry wins.
  const carrying = (bs: Block[]): Block[] => {
    const mends = live.current.doc.breaks;
    if (!mends) return bs;
    return bs.map((b) => ("text" in b.props || "cells" in b.props ? ({ ...b, props: { ...b.props, breaks: { ...mends, ...(b.props as { breaks?: Breaks }).breaks } } } as Block) : b));
  };
    return Object.assign(session, { freeSpot, add, served, sent, NO_PICTURE, unfit, upload, dropped, WEB_PICTURE, dropLink, landed, addInsert, addMaths, put, pending, wordsOf, carrying });
}
