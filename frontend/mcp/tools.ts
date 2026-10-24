import schema from "../../src/blattwerk/sheet.schema.json" with { type: "json" };
import type { Api } from "./api.ts";
import { Fail } from "./errors.ts";
import { sheetHandlers, text } from "./handlers.ts";

export type ToolDef = { name: string; description: string; inputSchema: Record<string, unknown> };
export type Content = { type: string; text?: string; data?: string; mimeType?: string }[];
export type ToolResult = { content: Content; isError?: boolean };

// The block types the MCP server writes. The others stay in the schema for the editor, not for Claude.
const KEPT_BLOCKS = ["text", "shape", "ruling", "name", "points", "symbol", "image", "maths", "table", "suchsel", "zahlenmauer", "zahlenhaus", "zahlenkette", "pfeilbild", "operatorfeld", "rechenrad", "rechentabelle", "magischesquadrat", "malquadrat", "zerlegungsfeld", "halbschriftlich", "zehnerfeld", "rechendreieck", "zahlenstrahl", "hunderterfeld", "uhr", "selbstkontrolle"];

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

export function tools(api: Api) {
  const docDefs = docDefinitions(schema);
  const props = propsSchema(schema);
  const blockTypes = schema.definitions.Block.properties.type.enum;
  const h = sheetHandlers(api);

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
        "Add a block to a page. Warnings: `overlaps block <id>` means it meets that block; `leaves the page's printable area` means it comes within 15 mm of an edge. Props per type: resource blattomat://okf/blocks/<type>.md.",
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
      name: "upload_picture",
      description:
        "Upload a picture (SVG text or base64 PNG, JPEG, WebP, GIF) into the teacher's account; place it with add_block, type image, props.upload. How: blattomat://okf/recipes/bild-zeichnen.md.",
      inputSchema: {
        type: "object",
        properties: {
          svg: { type: "string", description: "the SVG picture as text, with a viewBox and no entities" },
          data: { type: "string", description: "the picture's bytes as base64: PNG, JPEG, WebP or GIF" },
        },
      },
    },
    {
      name: "send_feedback",
      description:
        "Report a fault or missing feature in Blattomat that you hit (a block drawn wrong, valid input refused). Not for your own mistakes, not for a question. Write in German. Never quote text from the sheet, never write names from it.",
      inputSchema: {
        type: "object",
        properties: {
          text: { type: "string", description: "what you did, what you expected and what happened, in German" },
          sheet_id: { ...id, description: "the sheet you worked on, if any" },
        },
        required: ["text"],
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

  // A note to Blattomat's makers, sent as the teacher's feedback form sends it, with source "mcp".
  async function sendFeedback(args: any): Promise<Content> {
    const note = typeof args.text === "string" ? args.text.trim() : "";
    if (!note) throw new Fail("text must not be empty: say what went wrong.");
    const fields: Record<string, string> = { art: "feedback", text: note, source: "mcp" };
    if (args.sheet_id !== undefined) fields.sheet_id = String(args.sheet_id);
    const r = await api.form("/feedback", fields);
    if (r.status === 429) throw new Fail("Too many sends: 10 in 15 minutes at most. This one was not kept; send it again later.");
    h.expectOk(r);
    return text({ sent: true });
  }

  async function run(name: string, args: any): Promise<Content> {
    switch (name) {
      case "list_sheets": {
        const sheets = h.expectOk(await api.send("GET", "/sheets"));
        return text(sheets.map((s: any) => ({ id: s.id, title: s.title, version: s.version, updated: s.updated })));
      }
      case "get_sheet":
        return text(await h.readSheet(args.sheet_id));
      case "create_sheet":
        return h.createSheet(args);
      case "rename_sheet": {
        const r = await api.send("PATCH", `/sheets/${args.sheet_id}`, { title: args.title });
        h.expectOk(r, args.sheet_id);
        return text({ id: args.sheet_id, title: args.title });
      }
      case "duplicate_sheet": {
        const copy = h.expectOk(await api.send("POST", `/sheets/${args.sheet_id}/duplicate`), args.sheet_id);
        return text(await h.readSheet(copy.id));
      }
      case "replace_doc":
        return h.replaceDoc(args);
      case "add_block":
        return h.addBlock(args);
      case "update_block":
        return h.updateBlock(args);
      case "move_block":
        return h.moveBlock(args);
      case "delete_block":
        return h.deleteBlock(args);
      case "add_page":
        return h.addPage(args);
      case "set_page":
        return h.setPage(args);
      case "set_words":
        return h.setWords(args);
      case "render_preview":
        return h.previewPng(args);
      case "upload_picture":
        return h.uploadPicture(args);
      case "send_feedback":
        return sendFeedback(args);
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
