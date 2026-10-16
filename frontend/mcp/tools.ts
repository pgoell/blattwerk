import { readFileSync } from "node:fs";
import { isDeepStrictEqual } from "node:util";
import type { Api } from "./api.ts";
import { mathsHeight } from "../src/height.ts";
import type { MathsProps } from "../src/sheet.tsx";

export const INSTRUCTIONS = readFileSync(new URL("./instructions.md", import.meta.url), "utf8");

export type ToolDef = { name: string; description: string; inputSchema: Record<string, unknown> };
export type Content = { type: string; text?: string; data?: string; mimeType?: string }[];
export type ToolResult = { content: Content; isError?: boolean };

const TOKEN_MESSAGE = "The Blattomat token is not valid: make a new one on the account page.";
// The block types the MCP server writes. The others stay in the schema for the editor, not for Claude.
const KEPT_BLOCKS = ["text", "maths", "ruling"];
// The settings the server's /api/maths takes, read from a block's props.
const MATHS_KEYS = [
  "ops", "max", "count", "seed", "a", "b", "c", "carry", "rest", "format", "sides", "close", "equal",
  "numbers", "pvs", "brackets", "decimals", "money", "af", "bf", "cf", "family", "moves", "gaps", "zero",
  "one", "distinct", "small",
];

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
    if (typeof node.$ref === "string" && node.$ref.startsWith("#/definitions/")) {
      const name = node.$ref.slice("#/definitions/".length);
      if (!seen.has(name)) {
        seen.add(name);
        walk(defs[name]);
      }
    }
    Object.values(node).forEach(walk);
  };
  walk(defs.Doc);
  return Object.fromEntries(Object.entries(defs).filter(([name]) => seen.has(name)));
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

export function tools(api: Api) {
  const bases = new Map<number, Base>();
  const schema = JSON.parse(readFileSync(new URL("../../src/blattwerk/sheet.schema.json", import.meta.url), "utf8"));
  const docDefs = docDefinitions(schema);

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

  async function fillMaths(doc: any) {
    for (const page of doc.pages ?? []) {
      for (const block of page.blocks ?? []) {
        if (block.type !== "maths" || block.props?.exercises?.length) continue;
        const p = block.props;
        p.carry ??= "either";
        p.rest ??= false;
        p.format ??= "row";
        p.columns ??= 4;
        p.size ??= 14;
        p.seed ??= Math.floor(Math.random() * 2 ** 31);
        const settings: Record<string, unknown> = {};
        for (const key of MATHS_KEYS) if (p[key] !== undefined) settings[key] = p[key];
        const r = await api.send("POST", "/maths", settings);
        if (r.status === 422) throw new Fail(`maths block ${block.id}:\n${problems(r.body).join("\n")}`);
        const made = expectOk(r);
        p.exercises = made.exercises;
        p.loosen = made.loosen;
        block.h = mathsHeight(p as MathsProps);
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
      description: "Make a new worksheet, empty or from a template by name.",
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
        "Write the whole doc of a worksheet, with the version get_sheet gave. Maths blocks get their exercises from the server.",
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
      case "render_preview":
        return previewPng(args);
      default:
        throw new Fail(`No tool named ${name}.`);
    }
  }

  async function call(name: string, args: any): Promise<ToolResult> {
    try {
      return { content: (await run(name, args ?? {})).map((c) => (c.text === undefined ? c : { ...c, text: api.hide(c.text) })) };
    } catch (e) {
      const message = e instanceof Error ? e.message : String(e);
      return { content: [{ type: "text", text: api.hide(message) }], isError: true };
    }
  }

  return { list: defs, call };
}

function text(value: unknown): Content {
  return [{ type: "text", text: JSON.stringify(value, null, 2) }];
}
