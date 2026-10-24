import { isDeepStrictEqual } from "node:util";
import type { Api } from "./api.ts";
import { INSERTS, MATHS, filled, grown, topZ } from "../src/insert.ts";
import { fresh } from "../src/history.ts";
import { mathsHeight } from "../src/height.ts";
import { MARGIN, overFoot, sizeOf, tall, wordsIn } from "../src/sheet.tsx";
import { follow } from "../src/words.ts";
import { EDGE, heightsOf } from "../src/cells.ts";
import type { MathsProps } from "../src/sheet.tsx";
import { Fail, TOKEN_MESSAGE } from "./errors.ts";
import { dimensions } from "./picture.ts";

type Content = { type: string; text?: string; data?: string; mimeType?: string }[];
type Base = { version: number; doc: any };

// The settings the server's /api/maths takes, read from a block's props.
const MATHS_KEYS = [
  "ops", "max", "count", "seed", "a", "b", "c", "carry", "rest", "format", "sides", "close", "equal",
  "numbers", "pvs", "brackets", "decimals", "money", "af", "bf", "cf", "family", "moves", "gaps", "zero",
  "one", "distinct", "small",
];
// The types a Block's `props` may take, each with the seed it is drawn with when added.
const SEEDED = ["suchsel", "zahlenmauer", "zahlenhaus", "zahlenkette", "pfeilbild", "operatorfeld", "rechenrad", "rechentabelle", "magischesquadrat", "malquadrat", "zerlegungsfeld", "halbschriftlich", "zehnerfeld", "rechendreieck", "zahlenstrahl", "hunderterfeld", "uhr", "selbstkontrolle"] as const;


function problems(body: any): string[] {
  const detail = body?.detail;
  if (Array.isArray(detail?.problems)) return detail.problems;
  if (Array.isArray(detail)) return detail.map((e: any) => e.msg ?? JSON.stringify(e));
  if (typeof detail === "string") return [detail];
  return [typeof body === "string" ? body : JSON.stringify(body)];
}

function pick(sheet: any) {
  return { id: sheet.id, title: sheet.title, version: sheet.version, doc: sheet.doc };
}

// A block's box as it fills the page (a turned block by the box it fills, as the editor counts it), and whether two meet.
const boxOf = (b: any) => filled([b])[0];
const meets = (a: any, b: any) => a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h;

export function text(value: unknown): Content {
  return [{ type: "text", text: JSON.stringify(value, null, 2) }];
}

// The fine tools: read a sheet, check its version, change a copy, and write it back.
export function sheetHandlers(api: Api) {
  const bases = new Map<number, Base>();
  function expectOk(r: { status: number; body: any }, sheetId?: number) {
    if (r.status >= 200 && r.status < 300) return r.body;
    if (r.status === 401) throw new Fail(TOKEN_MESSAGE);
    if (r.status === 404 && sheetId !== undefined) throw new Fail(`No sheet with id ${sheetId}.`);
    throw new Fail(problems(r.body).join("\n"));
  }

  async function readSheet(id: number) {
    const sheet = pick(expectOk(await api.send("GET", `/sheets/${id}`), id));
    bases.set(id, { version: sheet.version, doc: sheet.doc });
    return sheet;
  }

  const stale = (had: number, now: number) =>
    `The teacher changed this sheet in the editor since you read it (you had version ${had}, it is now ${now}). Nothing was written. Call get_sheet and make your change on the new doc.`;

  // The one write path of the fine tools: read the sheet, check the version, change a fresh copy, PATCH it strictly.
  async function edit(tool: string, id: number, version: number, change: (doc: any) => any): Promise<{ version: number; out: any }> {
    const cur = pick(expectOk(await api.send("GET", `/sheets/${id}`), id));
    if (cur.version !== version) throw new Fail(stale(version, cur.version));
    const doc = structuredClone(cur.doc);
    const out = await change(doc);
    const r = await api.send("PATCH", `/sheets/${id}?strict=true`, { doc, version });
    if (r.status === 409) throw new Fail(stale(version, (await readSheet(id)).version));
    if (r.status === 422) throw new Fail(`${problems(r.body).join("\n")}\nFix these and call ${tool} again.`);
    // The version this write made, from its own answer: a read after it could already hold the teacher's next save.
    const saved = pick(expectOk(r, id));
    bases.set(id, { version: saved.version, doc: saved.doc });
    return { version: saved.version, out };
  }

  function pageAt(doc: any, n: number) {
    const count = doc.pages.length;
    if (!Number.isInteger(n) || n < 1 || n > count) throw new Fail(`No page ${n}. The sheet has ${count} pages.`);
    return doc.pages[n - 1];
  }

  function locate(doc: any, id: string) {
    for (const [i, page] of doc.pages.entries()) {
      const b = page.blocks.find((o: any) => o.id === id);
      if (b) return { n: i + 1, page, b };
    }
    const ids = doc.pages.flatMap((p: any) => p.blocks.map((o: any) => o.id));
    throw new Fail(`No block with id ${id}. The sheet's blocks: ${ids.length ? ids.join(", ") : "none"}.`);
  }

  // Warnings for block `b` on page `n`: what it meets and whether it leaves the page.
  function warnings(doc: any, n: number, b: any): string[] {
    const [W, H] = sizeOf(doc, n - 1);
    const out: string[] = [];
    // The printable area keeps the margin a new block keeps in the editor; a hundredth of a mm is rounding.
    const box = boxOf(b);
    const [lo, hiW, hiH] = [MARGIN - 0.01, W - MARGIN + 0.01, H - MARGIN + 0.01];
    if (box.x < lo || box.y < lo || box.x + box.w > hiW || box.y + box.h > hiH) out.push(`leaves the page's printable area (${MARGIN} mm from each edge)`);
    for (const o of doc.pages[n - 1].blocks) if (o.id !== b.id && meets(boxOf(o), boxOf(b))) out.push(`overlaps block ${o.id}`);
    return out;
  }

  // The height and the exercises of a maths block, from the server (or kept when it has its own exercises).
  async function makeMaths(b: any) {
    const p = b.props;
    p.carry ??= "either";
    p.rest ??= false;
    p.format ??= "row";
    p.columns ??= 4;
    p.size ??= 14;
    if (p.seed === undefined) p.seed = Math.floor(Math.random() * 2 ** 31);
    const settings: Record<string, unknown> = {};
    for (const key of MATHS_KEYS) if (p[key] !== undefined) settings[key] = p[key];
    const r = await api.send("POST", "/maths", settings);
    if (r.status === 422) throw new Fail(`maths block ${b.id}:\n${problems(r.body).join("\n")}`);
    const made = expectOk(r);
    p.exercises = made.exercises;
    p.loosen = made.loosen;
    b.h = mathsHeight(p as MathsProps);
  }

  async function fillMaths(doc: any) {
    for (const page of doc.pages ?? []) {
      for (const block of page.blocks ?? []) {
        if (block.type !== "maths" || block.props?.exercises?.length) continue;
        if (Object.keys(block.props ?? {}).length === 0) block.props = { ...MATHS.limits(Math.floor(Math.random() * 2 ** 31)), ...MATHS.look };
        await makeMaths(block);
      }
    }
  }

  async function replaceDoc(args: any): Promise<Content> {
    const id: number = args.sheet_id;
    const version: number = args.version;
    const doc = structuredClone(args.doc);
    await fillMaths(doc);
    let r = await api.send("PATCH", `/sheets/${id}?strict=true`, { doc, version });
    if (r.status === 409) {
      const fresh = pick(expectOk(await api.send("GET", `/sheets/${id}`), id));
      const base = bases.get(id);
      const sameAsRead = base !== undefined && base.version === version && isDeepStrictEqual(base.doc, fresh.doc);
      if (sameAsRead) r = await api.send("PATCH", `/sheets/${id}?strict=true`, { doc, version: fresh.version });
      if (!sameAsRead || r.status === 409) {
        throw new Fail(
          `The teacher changed this sheet in the editor since you read it (you had version ${version}, it is now ${fresh.version}). ` +
            "Nothing was written. Call get_sheet and make your change on the new doc.",
        );
      }
    }
    if (r.status === 422) {
      throw new Fail(`${problems(r.body).join("\n")}\nFix these and call replace_doc again.`);
    }
    expectOk(r, id);
    return text(await readSheet(id));
  }

  async function createSheet(args: any): Promise<Content> {
    let doc: any = { pages: [{ blocks: [] }], guides: { x: [], y: [] }, grid: 0 };
    if (args.template !== undefined) {
      const templates = expectOk(await api.send("GET", "/templates"));
      const found = templates.find((t: any) => t.name === args.template);
      if (!found) {
        const names = templates.map((t: any) => t.name).join(", ");
        throw new Fail(`No template named "${args.template}". Templates: ${names}`);
      }
      doc = found.doc;
    }
    const made = expectOk(await api.send("POST", "/sheets", { title: args.title, doc }));
    return text(await readSheet(made.id));
  }

  // A picture of this teacher's upload, sized as the editor's `sent()` sizes it: 100 mm wide, or less to keep its ratio.
  async function picture(upload: unknown) {
    if (!Number.isInteger(upload)) throw new Fail("An image needs props.upload, the id of one of the teacher's uploads.");
    const r = await api.bytes(`/uploads/${upload}`);
    if (r.status === 404) throw new Fail(`No upload with id ${upload}.`);
    if (r.status !== 200) throw new Fail(`Upload ${upload} could not be read.`);
    const [width, height] = dimensions(Buffer.from(r.body, "base64"));
    const ratio = width / height;
    const w = Math.round(Math.min(100, 100 * ratio) * 100) / 100;
    return { w, h: Math.round((w / ratio) * 100) / 100, type: "image", props: { upload, ratio, cut: [0, 0, 0, 0] } };
  }

  // A new block of `type` as the editor's insert button makes it, its props laid on as the panel does.
  async function newBlock(args: any, doc: any, page: any) {
    const type: string = args.type;
    const seed = args.props?.seed ?? Math.floor(Math.random() * 2 ** 31);
    const base: any =
      type === "image" ? await picture(args.props?.upload)
      : type === "text" ? INSERTS.text()
      : type === "shape" ? INSERTS.shape(args.props?.kind ?? "rect")
      : type === "ruling" ? INSERTS.ruling()
      : type === "name" ? INSERTS.name()
      : type === "points" ? INSERTS.points()
      : type === "symbol" ? INSERTS.symbol()
      : type === "table" ? INSERTS.table()
      : type === "maths" ? { w: MATHS.w, h: 10, type: "maths", props: { ...MATHS.limits(seed), ...MATHS.look } }
      : (SEEDED as readonly string[]).includes(type) ? (INSERTS as any)[type](seed)
      : undefined;
    if (!base) throw new Fail(`Type ${type} is not one the tools add.`);
    // As in the editor: the block lands, takes the size asked for, and then its props, so it grows at that width.
    const b: any = { id: crypto.randomUUID(), type, x: args.x, y: args.y, w: args.w ?? base.w, h: args.h ?? base.h, z: topZ(page.blocks), locked: false, props: base.props };
    const next = { ...b, props: { ...b.props, ...fresh(b, args.props ?? {}) } };
    if (type !== "maths") return { ...next, ...grown(b, next, doc, sizeOf(doc, doc.pages.indexOf(page))[1]) };
    await makeMaths(next);
    return { ...next, h: args.h ?? next.h };
  }

  // Lays the props of a change on a block as the editor's panel does; a maths block whose settings change gets new exercises.
  async function patched(doc: any, b: any, changes: object) {
    const next = { ...b, props: { ...b.props, ...fresh(b, changes) } };
    const H = sizeOf(doc, doc.pages.findIndex((p: any) => p.blocks.includes(b)))[1];
    if (b.type === "maths") {
      // New settings for the exercises bring new ones, from the block's seed unless one is given, as the panel does.
      const changed = MATHS_KEYS.some((key) => key in changes && !isDeepStrictEqual((b.props as any)[key], (changes as any)[key]));
      if (changed) {
        next.props = { ...next.props, exercises: undefined, loosen: undefined };
        await makeMaths(next);
      }
      // The height follows the exercises when they need more or less room; a change past the page's foot is refused.
      if (overFoot(b, next.props, H)) throw new Fail(`Block ${b.id} would reach past the page's foot. Nothing was written: move it up or ask for fewer exercises.`);
      const need = mathsHeight(next.props as MathsProps);
      return { ...next, h: b.h, ...(need !== mathsHeight(b.props) && tall(b, need)) };
    }
    if (b.type === "image" && "upload" in changes) {
      // Another picture: it must be this teacher's, and the block takes its shape.
      const { props } = await picture((changes as any).upload);
      next.props = { ...next.props, ratio: props.ratio };
      return { ...next, h: Math.round((b.w / props.ratio) * 100) / 100 };
    }
    return { ...next, ...grown(b, next, doc, H) };
  }

  async function addBlock(args: any): Promise<Content> {
    const { version, out } = await edit("add_block", args.sheet_id, args.version, async (doc: any) => {
      const page = pageAt(doc, args.page);
      const b = await newBlock(args, doc, page);
      page.blocks.push(b);
      return { block: b, warnings: warnings(doc, args.page, b) };
    });
    return text({ version, block: out.block, warnings: out.warnings });
  }

  async function updateBlock(args: any): Promise<Content> {
    const { version, out } = await edit("update_block", args.sheet_id, args.version, async (doc: any) => {
      const { n, page, b } = locate(doc, args.block_id);
      if (b.locked) throw new Fail(`Block ${b.id} is locked. Nothing was written.`);
      const next = await patched(doc, b, args.props ?? {});
      page.blocks[page.blocks.indexOf(b)] = next;
      return { block: next, warnings: warnings(doc, n, next) };
    });
    return text({ version, block: out.block, warnings: out.warnings });
  }

  async function moveBlock(args: any): Promise<Content> {
    const { version, out } = await edit("move_block", args.sheet_id, args.version, async (doc: any) => {
      const { n, b } = locate(doc, args.block_id);
      if (b.locked) throw new Fail(`Block ${b.id} is locked. Nothing was written.`);
      // A table with row heights keeps them in proportion to its height, as the editor's `place` does.
      const rows = b.type === "table" && args.h !== undefined && b.h > EDGE && args.h !== b.h ? heightsOf(b.props) : undefined;
      if (rows) b.props = { ...b.props, rows: rows.map((h) => (h * (args.h - EDGE)) / (b.h - EDGE)) };
      Object.assign(b, { x: args.x, y: args.y, ...(args.w !== undefined && { w: args.w }), ...(args.h !== undefined && { h: args.h }) });
      return { block: b, warnings: warnings(doc, n, b) };
    });
    return text({ version, block: out.block, warnings: out.warnings });
  }

  async function deleteBlock(args: any): Promise<Content> {
    const { version } = await edit("delete_block", args.sheet_id, args.version, (doc: any) => {
      const { page, b } = locate(doc, args.block_id);
      if (b.locked) throw new Fail(`Block ${b.id} is locked. Nothing was written.`);
      page.blocks.splice(page.blocks.indexOf(b), 1);
    });
    return text({ version, deleted: args.block_id, warnings: [] });
  }

  async function addPage(args: any): Promise<Content> {
    const { version, out } = await edit("add_page", args.sheet_id, args.version, (doc: any) => {
      const after = args.after ?? doc.pages.length;
      if (!Number.isInteger(after) || after < 0 || after > doc.pages.length) throw new Fail(`No page ${after}. The sheet has ${doc.pages.length} pages.`);
      doc.pages.splice(after, 0, { blocks: [] });
      return after + 1;
    });
    return text({ version, page: out, warnings: [] });
  }

  async function setPage(args: any): Promise<Content> {
    const { version, out } = await edit("set_page", args.sheet_id, args.version, (doc: any) => {
      const page = pageAt(doc, args.page);
      if (args.landscape !== undefined) page.landscape = args.landscape;
      if (args.grid !== undefined) doc.grid = args.grid;
      if (args.guides !== undefined) page.guides = args.guides;
      const found = new Set<string>();
      for (const b of page.blocks) for (const w of warnings(doc, args.page, b)) found.add(w);
      return [...found];
    });
    return text({ version, page: args.page, warnings: out });
  }

  async function setWords(args: any): Promise<Content> {
    const { version, out } = await edit("set_words", args.sheet_id, args.version, (doc: any) => {
      // An empty list is sent as is: the server stores no list for it, and a missing key would keep the stored one.
      // As the editor's list field: the words as the sheet reads them, and every page's blocks, since a list runs on.
      doc.words = args.words;
      const words = wordsIn(doc);
      const all = doc.pages.flatMap((p: any) => p.blocks);
      doc.pages.forEach((page: any, i: number) => {
        const [W, H] = sizeOf(doc, i);
        page.blocks = follow(page.blocks, words, W, H, all);
      });
      return args.words;
    });
    return text({ version, words: out, warnings: [] });
  }

  async function previewPng(args: any): Promise<Content> {
    const id: number = args.sheet_id;
    const page = args.page ?? 1;
    const outlines = args.outlines ?? false;
    const r = await api.bytes(`/sheets/${id}/preview.png?page=${page}&outlines=${outlines}`);
    if (r.status === 200) return [{ type: "image", data: r.body, mimeType: "image/png" }];
    if (r.status === 401) throw new Fail(TOKEN_MESSAGE);
    if (r.status === 404) {
      let detail: unknown;
      try {
        detail = JSON.parse(r.body).detail;
      } catch {
        detail = undefined;
      }
      if (typeof detail === "string") throw new Fail(detail);
      throw new Fail(`No sheet with id ${id}.`);
    }
    throw new Fail(r.body);
  }

  // A picture into the teacher's account: SVG text, or the base64 of a raster picture. Its id goes to add_block.
  async function uploadPicture(args: any): Promise<Content> {
    const { svg, data } = args;
    if ((svg === undefined) === (data === undefined)) throw new Fail("Give one of svg (SVG text) or data (base64 of a PNG, JPEG, WebP or GIF), not both.");
    let bytes: Buffer;
    let type: string;
    if (svg !== undefined) {
      if (typeof svg !== "string") throw new Fail("svg must be the text of an SVG picture.");
      bytes = Buffer.from(svg, "utf8");
      type = "image/svg+xml";
    } else {
      // Strict: Buffer.from drops a space or a stray character, so the bytes would be another picture. Decoding and
      // encoding again gives the text back only when it is base64 as written (a regex overflows on a picture this size).
      if (typeof data !== "string") throw new Fail("data must be the picture as base64 text.");
      bytes = Buffer.from(data, "base64");
      if (bytes.toString("base64") !== data) throw new Fail("data must be base64, with no spaces or line breaks.");
      type = "application/octet-stream";
    }
    const r = await api.upload(bytes, type);
    if (r.status === 413) throw new Fail("The picture is too large: 15 MB at most, an SVG 2 MB.");
    if (r.status === 415) throw new Fail("The server does not take this picture: PNG, JPEG, WebP, GIF, or SVG with a viewBox (no entities).");
    const made = expectOk(r);
    // The ratio of what the server stored, which add_block reads too: a cleaned SVG may have taken its size from the viewBox.
    const { props } = await picture(made.id);
    return text({ upload: made.id, ratio: props.ratio });
  }

  // A note to Blattomat's makers, sent as the teacher's feedback form sends it, with source "mcp".
  return {
    expectOk, readSheet, createSheet, replaceDoc, addBlock, updateBlock, moveBlock,
    deleteBlock, addPage, setPage, setWords, previewPng, uploadPicture,
  };
}
