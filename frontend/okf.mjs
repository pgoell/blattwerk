// Writes one OKF reference page per block type, and the index of them, from the sheet's JSON Schema
// (src/blattwerk/sheet.schema.json) into docs/okf/blocks/. With --check it writes nothing and fails where a page
// differs from what the schema gives, or is missing or extra: `mise run lint` runs it so. --dir <path> is the folder
// to write or check, for a test.
import { existsSync, mkdirSync, readdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

const SCHEMA = new URL("../src/blattwerk/sheet.schema.json", import.meta.url);
const args = process.argv.slice(2);
const check = args.includes("--check");
const at = args.indexOf("--dir");
const dir = at >= 0 ? resolve(args[at + 1]) : fileURLToPath(new URL("../docs/okf/blocks/", import.meta.url));

const defs = JSON.parse(readFileSync(SCHEMA, "utf8")).definitions;
const refName = (ref) => ref.split("/").pop();

// The type a field holds, as a word: string, number, list of string, or the names of its alternatives.
function typeOf(s) {
  if (s.$ref) return typeOf(defs[refName(s.$ref)]);
  if (s.anyOf) return [...new Set(s.anyOf.map(typeOf))].join(" or ");
  if (s.const !== undefined) return typeof s.const;
  if (s.enum) return s.type ?? typeof s.enum[0];
  if (s.type === "array") return `list of ${Array.isArray(s.items) ? s.items.map(typeOf).join(" and ") : typeOf(s.items)}`;
  return s.type;
}

// The values a prop takes: its enum, its constant, or its range. "" when it takes any value.
function valuesOf(s) {
  const t = s.$ref ? { ...defs[refName(s.$ref)], ...s } : s;
  if (t.anyOf) return t.anyOf.map(valuesOf).filter(Boolean).join(" or ");
  if (t.enum) return t.enum.map((v) => `\`${v}\``).join(", ");
  if (t.const !== undefined) return `\`${t.const}\``;
  if (t.type === "array" && t.items && !Array.isArray(t.items)) return valuesOf(t.items);
  if (t.minimum !== undefined && t.maximum !== undefined) return `${t.minimum} to ${t.maximum}`;
  if (t.minimum !== undefined) return `at least ${t.minimum}`;
  if (t.maximum !== undefined) return `at most ${t.maximum}`;
  return "";
}

const descriptionOf = (s) => s.description ?? (s.$ref ? defs[refName(s.$ref)].description : undefined) ?? "";
const firstSentence = (text) => text.match(/^.*?[.!?](?=\s|$)/s)?.[0] ?? text;

const cell = (text) => String(text).replace(/\|/g, "\\|").replace(/\n/g, " ");
const row = (cells) => `| ${cells.map(cell).join(" | ")} |`;
const table = (header, rows) => [row(header), row(header.map(() => "---")), ...rows.map(row)].join("\n");

// Each block type, in the enum's order, with the schema of its block.
const types = defs.Block.properties.type.enum;
const blockOf = new Map(defs.Block.allOf.map((branch) => [branch.if.properties.type.const, defs[refName(branch.then.$ref)]]));

const BOX_NOTE = "Every block has the box fields of the [page model](../page-model.md). This page lists the rest.";

function summaryOf(type, propsText) {
  return propsText ? firstSentence(propsText).trim() : `The ${type} block.`;
}

function page(type) {
  const block = blockOf.get(type);
  const propsSchema = block.properties.props;
  const propsDef = propsSchema.$ref ? defs[refName(propsSchema.$ref)] : propsSchema;
  const propsText = descriptionOf(propsSchema);
  const summary = summaryOf(type, propsText);

  const fields = Object.entries(block.properties)
    .filter(([key]) => key !== "props" && key !== "type")
    .map(([key, s]) => [key, typeOf(s), block.required.includes(key) ? "yes" : "no", descriptionOf(s)]);
  const props = Object.entries(propsDef.properties ?? {}).map(([key, s]) => [
    key,
    typeOf(s),
    valuesOf(s),
    (propsDef.required ?? []).includes(key) ? "yes" : "no",
    descriptionOf(s),
  ]);

  const frontmatter = [
    "---",
    "type: Reference",
    `title: ${JSON.stringify(`Block: ${type}`)}`,
    `description: ${JSON.stringify(summary)}`,
    `tags: [block, ${type}]`,
    `covers: [${type}]`,
    `generated: { by: "process:frontend/okf.mjs" }`,
    "---",
  ];
  const body = [
    `# ${type}`,
    ...(propsText ? [propsText] : []),
    BOX_NOTE,
    "# Schema",
    "## Block fields",
    table(["Field", "Type", "Required", "Description"], fields),
    "## Props",
    table(["Prop", "Type", "Values", "Required", "Description"], props),
    "# Examples",
    "An empty block of this type as `add_block` takes it:",
    `\`\`\`json\n{"type": "${type}", "props": {}}\n\`\`\``,
  ];
  return `${frontmatter.join("\n")}\n\n${body.join("\n\n")}\n`;
}

function index() {
  const lines = types.map((type) => {
    const propsSchema = blockOf.get(type).properties.props;
    return `* [${type}](${type}.md): ${summaryOf(type, descriptionOf(propsSchema))}`;
  });
  return [
    "# Blocks",
    "Each page lists one block type's props, generated from the sheet's schema by `frontend/okf.mjs`. Do not edit them by hand: run `mise run schema`.",
    ...lines,
  ].join("\n\n") + "\n";
}

const pages = new Map(types.map((type) => [`${type}.md`, page(type)]));
pages.set("index.md", index());
const extra = existsSync(dir) ? readdirSync(dir).filter((name) => name.endsWith(".md") && !pages.has(name)) : [];

if (check) {
  const problems = [];
  for (const [name, text] of pages) {
    const path = resolve(dir, name);
    if (!existsSync(path)) problems.push(`${name}: missing`);
    else if (readFileSync(path, "utf8") !== text) problems.push(`${name}: differs from the schema`);
  }
  for (const name of extra) problems.push(`${name}: extra, the schema has no such page`);
  if (problems.length) {
    console.error(`${problems.join("\n")}\ndocs/okf/blocks differs from the schema: run mise run schema and commit it.`);
    process.exit(1);
  }
} else {
  mkdirSync(dir, { recursive: true });
  for (const [name, text] of pages) writeFileSync(resolve(dir, name), text);
  for (const name of extra) rmSync(resolve(dir, name));
}
