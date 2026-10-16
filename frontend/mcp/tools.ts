import { readFileSync } from "node:fs";
import { isDeepStrictEqual } from "node:util";
import type { Api } from "./api.ts";
import { INSERTS, MATHS, filled, grown, topZ } from "../src/insert.ts";
import { fresh } from "../src/history.ts";
import { mathsHeight } from "../src/height.ts";
import { MARGIN, overFoot, sizeOf, tall, wordsIn } from "../src/sheet.tsx";
import { follow } from "../src/words.ts";
import { EDGE, heightsOf } from "../src/cells.ts";
import type { MathsProps } from "../src/sheet.tsx";

export type ToolDef = { name: string; description: string; inputSchema: Record<string, unknown> };
export type Content = { type: string; text?: string; data?: string; mimeType?: string }[];
export type ToolResult = { content: Content; isError?: boolean };

const TOKEN_MESSAGE = "The Blattomat token is not valid: make a new one on the account page.";
// The block types the MCP server writes. The others stay in the schema for the editor, not for Claude.
const KEPT_BLOCKS = ["text", "shape", "ruling", "name", "points", "symbol", "image", "maths", "table", "suchsel", "zahlenmauer", "rechendreieck", "zahlenstrahl", "hunderterfeld", "uhr", "selbstkontrolle"];
// The settings the server's /api/maths takes, read from a block's props.
const MATHS_KEYS = [
  "ops", "max", "count", "seed", "a", "b", "c", "carry", "rest", "format", "sides", "close", "equal",
  "numbers", "pvs", "brackets", "decimals", "money", "af", "bf", "cf", "family", "moves", "gaps", "zero",
  "one", "distinct", "small",
];
// The types a Block's `props` may take, each with the seed it is drawn with when added.
const SEEDED = ["suchsel", "zahlenmauer", "rechendreieck", "zahlenstrahl", "hunderterfeld", "uhr", "selbstkontrolle"] as const;

// An error the teacher's Claude reads as the tool's answer.
class Fail extends Error {}

type Base = { version: number; doc: any };

export function docDefinitions(schema: any): Record<string, any> {
  const defs = structuredClone(schema.definitions);
  defs.Block.allOf = defs.Block.allOf.filter((entry: any) => KEPT_BLOCKS.includes(entry.if.properties.type.const));
  const seen = new Set<string>();
  const walk = (node: any): void => {
    if (Array.isArray(node)) return node.forEach(walk);
    if (!node || typeof node !== "object") return;
    // The schema is draft 7; a tool's schema is draft 2020-12, where a list of fixed length says `prefixItems`.
    if (Array.isArray(node.items)) {
      node.prefixItems = node.items;
      delete node.items;
    }
    if (typeof node.$ref === "string" && node.$ref.startsWith("#/definitions/")) {
      const name = node.$ref.slice("#/definitions/".length);
      if (!seen.has(name)) {
        seen.add(name);
        walk(defs[name]);
      }
    }
    Object.values(node).forEach(walk);
  };
  // The tool's schema points at Doc itself, so it stays too.
  seen.add("Doc");
  walk(defs.Doc);
  return Object.fromEntries(Object.entries(defs).filter(([name]) => seen.has(name)));
}

// The props of each block type as the tools take them: the schema's `<Type>Props` with `required` removed, since
// Claude sends partial props. Returns the anyOf variants and the definitions they point at.
function propsSchema(schema: any) {
  // docDefinitions makes the list types draft 2020-12, so the copies here are valid too.
  const defs = docDefinitions(schema);
  const own: Record<string, any> = {};
  const variants = defs.Block.allOf
    .filter((e: any) => KEPT_BLOCKS.includes(e.if.properties.type.const))
    .map((e: any) => {
      const props = defs[e.then.$ref.slice("#/definitions/".length)].properties.props;
      // Some types keep their props inline in the Block definition, not in a `<Type>Props` one.
      if (typeof props.$ref !== "string") return withoutRequired(props);
      const name = props.$ref.slice("#/definitions/".length);
      own[name] = withoutRequired(defs[name]);
      return { $ref: props.$ref };
    });
  return { variants, definitions: own };
}

function withoutRequired(schema: any) {
  const { required: _required, ...rest } = schema;
  return rest;
}

// The server's own messages: a FastAPI list of {msg}, a {problems} list, or a plain detail text.
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

export function tools(api: Api) {
  const bases = new Map<number, Base>();
  const schema = JSON.parse(readFileSync(new URL("../../src/blattwerk/sheet.schema.json", import.meta.url), "utf8"));
  const docDefs = docDefinitions(schema);
  const props = propsSchema(schema);
  const blockTypes = schema.definitions.Block.properties.type.enum;

  // Any answer that is not a success becomes an error for the teacher's Claude, or throws.
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

  const id = { type: "integer" };
  const version = { type: "integer", description: "the version get_sheet or the last write gave" };
  const defs: ToolDef[] = [
    {
      name: "list_sheets",
      description: "List the teacher's worksheets: id, title, version and last update.",
      inputSchema: { type: "object", properties: {} },
    },
    {
      name: "get_sheet",
      description: "Read one worksheet with its doc and version. Call it before replace_doc.",
      inputSchema: {
        type: "object",
        properties: { sheet_id: { type: "integer" } },
        required: ["sheet_id"],
      },
    },
    {
      name: "create_sheet",
      description:
        "Make a new worksheet, empty or from a template by name. Read blattomat://okf/page-model.md first.",
      inputSchema: {
        type: "object",
        properties: { title: { type: "string" }, template: { type: "string", description: "a template's name" } },
        required: ["title"],
      },
    },
    {
      name: "rename_sheet",
      description: "Change a worksheet's title.",
      inputSchema: {
        type: "object",
        properties: { sheet_id: { type: "integer" }, title: { type: "string" } },
        required: ["sheet_id", "title"],
      },
    },
    {
      name: "duplicate_sheet",
      description: "Copy a worksheet. Returns the copy.",
      inputSchema: { type: "object", properties: { sheet_id: { type: "integer" } }, required: ["sheet_id"] },
    },
    {
      name: "replace_doc",
      description:
        "Write the whole doc of a worksheet, with the version get_sheet gave. Maths blocks get their exercises from the server. Whole sheets to start from: blattomat://okf/recipes/index.md.",
      inputSchema: {
        type: "object",
        properties: {
          sheet_id: { type: "integer" },
          version: { type: "integer", description: "the version get_sheet gave" },
          doc: { $ref: "#/definitions/Doc" },
        },
        required: ["sheet_id", "version", "doc"],
        definitions: docDefs,
      },
    },
    {
      name: "add_block",
      description:
        "Add a block to a page. Warnings: `overlaps block <id>` means it meets that block; `leaves the page` means it goes past the page's edge. Props per type: resource blattomat://okf/blocks/<type>.md.",
      inputSchema: {
        type: "object",
        properties: {
          sheet_id: id,
          version,
          page: { type: "integer", minimum: 1, description: "1-based" },
          type: { enum: blockTypes },
          props: { anyOf: props.variants, description: "the block's settings; partial is fine" },
          x: { type: "number" },
          y: { type: "number" },
          w: { type: "number" },
          h: { type: "number" },
        },
        required: ["sheet_id", "version", "page", "type", "x", "y"],
        definitions: { ...docDefs, ...props.definitions },
      },
    },
    {
      name: "update_block",
      description:
        "Change a block's props. Warnings mean as for add_block. A locked block is refused. Props per type: resource blattomat://okf/blocks/<type>.md.",
      inputSchema: {
        type: "object",
        properties: {
          sheet_id: id,
          version,
          block_id: { type: "string" },
          props: { anyOf: props.variants, description: "the props to change" },
        },
        required: ["sheet_id", "version", "block_id", "props"],
        definitions: { ...docDefs, ...props.definitions },
      },
    },
    {
      name: "move_block",
      description: "Move or resize a block. Warnings mean as for add_block. A locked block is refused.",
      inputSchema: {
        type: "object",
        properties: {
          sheet_id: id,
          version,
          block_id: { type: "string" },
          x: { type: "number" },
          y: { type: "number" },
          w: { type: "number" },
          h: { type: "number" },
        },
        required: ["sheet_id", "version", "block_id", "x", "y"],
      },
    },
    {
      name: "delete_block",
      description: "Remove a block. A locked block is refused.",
      inputSchema: {
        type: "object",
        properties: { sheet_id: id, version, block_id: { type: "string" } },
        required: ["sheet_id", "version", "block_id"],
      },
    },
    {
      name: "add_page",
      description: "Add an empty page after page `after` (1-based), by default at the end.",
      inputSchema: {
        type: "object",
        properties: { sheet_id: id, version, after: { type: "integer", minimum: 0 } },
        required: ["sheet_id", "version"],
      },
    },
    {
      name: "set_page",
      description: "Set a page's orientation, its guide lines, or the sheet's grid in mm. Warns of blocks that leave the page.",
      inputSchema: {
        type: "object",
        properties: {
          sheet_id: id,
          version,
          page: { type: "integer", minimum: 1 },
          landscape: { type: "boolean" },
          grid: { type: "number", description: "the sheet's grid in mm" },
          guides: schema.definitions.Guides,
        },
        required: ["sheet_id", "version", "page"],
      },
    },
    {
      name: "set_words",
      description:
        "Set the sheet's word list (doc.words; an empty list removes it). Linked rulings grow a row per word. Warnings: none.",
      inputSchema: {
        type: "object",
        properties: { sheet_id: id, version, words: { type: "array", items: { type: "string" } } },
        required: ["sheet_id", "version", "words"],
      },
    },
    {
      name: "render_preview",
      description: "Look at one page of a worksheet as a PNG.",
      inputSchema: {
        type: "object",
        properties: {
          sheet_id: { type: "integer" },
          page: { type: "integer", minimum: 1, default: 1 },
          outlines: { type: "boolean", default: false, description: "draw each block's box" },
        },
        required: ["sheet_id"],
      },
    },
  ];

  async function run(name: string, args: any): Promise<Content> {
    switch (name) {
      case "list_sheets": {
        const sheets = expectOk(await api.send("GET", "/sheets"));
        return text(sheets.map((s: any) => ({ id: s.id, title: s.title, version: s.version, updated: s.updated })));
      }
      case "get_sheet":
        return text(await readSheet(args.sheet_id));
      case "create_sheet":
        return createSheet(args);
      case "rename_sheet": {
        const r = await api.send("PATCH", `/sheets/${args.sheet_id}`, { title: args.title });
        expectOk(r, args.sheet_id);
        return text({ id: args.sheet_id, title: args.title });
      }
      case "duplicate_sheet": {
        const copy = expectOk(await api.send("POST", `/sheets/${args.sheet_id}/duplicate`), args.sheet_id);
        return text(await readSheet(copy.id));
      }
      case "replace_doc":
        return replaceDoc(args);
      case "add_block":
        return addBlock(args);
      case "update_block":
        return updateBlock(args);
      case "move_block":
        return moveBlock(args);
      case "delete_block":
        return deleteBlock(args);
      case "add_page":
        return addPage(args);
      case "set_page":
        return setPage(args);
      case "set_words":
        return setWords(args);
      case "render_preview":
        return previewPng(args);
      default:
        throw new Fail(`No tool named ${name}.`);
    }
  }

  async function call(name: string, args: any): Promise<ToolResult> {
    try {
      // The SDK does not check arguments against the schema, and these go into the URL.
      for (const key of ["sheet_id", "page"]) {
        if (args?.[key] !== undefined && !Number.isInteger(args[key])) throw new Fail(`${key} must be a whole number.`);
      }
      if (args?.outlines !== undefined && typeof args.outlines !== "boolean") throw new Fail("outlines must be true or false.");
      return { content: (await run(name, args ?? {})).map((c) => (c.text === undefined ? c : { ...c, text: api.hide(c.text) })) };
    } catch (e) {
      const message = e instanceof Error ? e.message : String(e);
      return { content: [{ type: "text", text: api.hide(message) }], isError: true };
    }
  }

  return { list: defs, call };
}

// The EXIF orientation (tag 0x0112 of the first IFD) of the TIFF block at `tiff`, or 1 when it has none.
function orientation(buf: Buffer, tiff: number): number {
  const le = buf.subarray(tiff, tiff + 2).toString("latin1") === "II";
  const u16 = (at: number) => (le ? buf.readUInt16LE(at) : buf.readUInt16BE(at));
  const u32 = (at: number) => (le ? buf.readUInt32LE(at) : buf.readUInt32BE(at));
  const ifd = tiff + u32(tiff + 4);
  for (let i = 0; i < u16(ifd); i++) {
    const entry = ifd + 2 + 12 * i;
    if (u16(entry) === 0x0112) return u16(entry + 8);
  }
  return 1;
}

// Width and height in pixels from a picture's header: PNG, GIF, JPEG or WebP, as the browser shows it.
function dimensions(buf: Buffer): [number, number] {
  if (buf.subarray(0, 8).equals(Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a])))
    return [buf.readUInt32BE(16), buf.readUInt32BE(20)];
  if (buf.subarray(0, 3).toString("latin1") === "GIF") return [buf.readUInt16LE(6), buf.readUInt16LE(8)];
  if (buf[0] === 0xff && buf[1] === 0xd8) {
    let at = 2;
    // A photo taken upright says so in its EXIF orientation (5 to 8): the browser, and so the editor, turns it.
    let turned = false;
    while (at + 9 < buf.length) {
      if (buf[at] !== 0xff) throw new Fail("The picture's header is broken.");
      const marker = buf[at + 1];
      if (marker === 0xe1 && buf.subarray(at + 4, at + 10).toString("latin1") === "Exif\0\0") turned = orientation(buf, at + 10) >= 5;
      // The frame headers (SOF0 to SOF15, but not DHT, JPG and DAC) hold the size.
      if (marker >= 0xc0 && marker <= 0xcf && ![0xc4, 0xc8, 0xcc].includes(marker)) {
        const [w, h] = [buf.readUInt16BE(at + 7), buf.readUInt16BE(at + 5)];
        return turned ? [h, w] : [w, h];
      }
      at += 2 + buf.readUInt16BE(at + 2);
    }
  }
  if (buf.subarray(0, 4).toString("latin1") === "RIFF" && buf.subarray(8, 12).toString("latin1") === "WEBP") {
    const chunk = buf.subarray(12, 16).toString("latin1");
    if (chunk === "VP8X") return [buf.readUIntLE(24, 3) + 1, buf.readUIntLE(27, 3) + 1];
    if (chunk === "VP8L") {
      const bits = buf.readUInt32LE(21);
      return [(bits & 0x3fff) + 1, ((bits >> 14) & 0x3fff) + 1];
    }
    if (chunk === "VP8 ") return [buf.readUInt16LE(26) & 0x3fff, buf.readUInt16LE(28) & 0x3fff];
  }
  throw new Fail("The picture is not a PNG, GIF, JPEG or WebP.");
}

function text(value: unknown): Content {
  return [{ type: "text", text: JSON.stringify(value, null, 2) }];
}
