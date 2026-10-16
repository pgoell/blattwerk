// Writes the JSON Schema of a sheet's document from the types in src/sheet.tsx to src/blattwerk/sheet.schema.json,
// where the server checks every saved document against it. With --check it writes nothing and fails where the file
// differs from what the types give, or where a field has no description: `mise run lint` runs it so.
import { readFileSync, writeFileSync } from "node:fs";
import { createGenerator } from "ts-json-schema-generator";

const OUT = new URL("../src/blattwerk/sheet.schema.json", import.meta.url);
// A field the types do not name passes: a tab opened before a deploy, or a sheet a later build wrote, must still
// save. The check refuses only what breaks a sheet: a wrong type, a number out of range, a field that is missing.
const schema = createGenerator({ path: "src/sheet.tsx", tsconfig: "tsconfig.json", type: "Doc", skipTypeCheck: true, additionalProperties: true }).createSchema("Doc");
const defs = schema.definitions;

// A block is one of 16 types. As an anyOf a wrong prop would read "not valid under any of the given schemas": the
// type picks the one schema each block answers to, so an error names the prop and what it must be.
const types = defs.Block.anyOf.map(({ $ref }) => defs[$ref.split("/").pop()].properties.type.const);
// What every block has, whatever its type: a block of a type nobody knows needs it too, for the editor to open it.
const box = ["id", "x", "y", "w", "h", "props"];
const first = defs[defs.Block.anyOf[0].$ref.split("/").pop()].properties;
defs.Block = {
  description: defs.Block.description,
  type: "object",
  required: ["type", ...box],
  properties: {
    type: { description: "What the block is; the other fields depend on it.", type: "string", enum: types },
    ...Object.fromEntries(box.map((key) => [key, { description: first[key].description, type: key === "id" ? "string" : key === "props" ? "object" : "number" }])),
    props: { description: "The block's own settings; which fields it holds depends on `type`.", type: "object" },
  },
  allOf: defs.Block.anyOf.map((ref, i) => ({ if: { properties: { type: { const: types[i] } } }, then: ref })),
};

// Saved sheets that differ from the types, which the schema still takes. The built-in maths templates
// (src/blattwerk/templates.py) make maths blocks with no `a` and `b`, and the editor fills those in on open. A table
// with no `line` keeps the colour of what it lies on.
const LOOSE = { MathsProps: ["a", "b"] };
for (const [name, fields] of Object.entries(LOOSE)) defs[name].required = defs[name].required.filter((field) => !fields.includes(field));
const table = defs.TableBlock.properties.props;
table.required = table.required.filter((field) => field !== "line");
// A border thinner than the menu's 0.25 mm prints as thin as it is set.
for (const props of [defs.TextProps, defs.ShapeBlock.properties.props]) delete props.properties.strokeWidth.minimum;

// That every field has a description, tests/test_schema.py checks.
const text = JSON.stringify(schema, null, 2) + "\n";
if (process.argv.includes("--check")) {
  let was = "";
  try {
    was = readFileSync(OUT, "utf8");
  } catch {}
  if (was !== text) {
    console.error("src/blattwerk/sheet.schema.json differs from the types in frontend/src: run `mise run schema` and commit it.");
    process.exit(1);
  }
} else writeFileSync(OUT, text);
