// Writes the JSON Schema of a sheet's document from the types in src/sheet.tsx to src/blattwerk/sheet.schema.json,
// where the server checks every saved document against it. With --check it writes nothing and fails where the file
// differs from what the types give, or where a field has no description: `mise run lint` runs it so.
import { readFileSync, writeFileSync } from "node:fs";
import { createGenerator } from "ts-json-schema-generator";

const OUT = new URL("../src/blattwerk/sheet.schema.json", import.meta.url);
const schema = createGenerator({ path: "src/sheet.tsx", tsconfig: "tsconfig.json", type: "Doc", skipTypeCheck: true }).createSchema("Doc");
const defs = schema.definitions;

// A block is one of 16 types. As an anyOf a wrong prop would read "not valid under any of the given schemas": the
// type picks the one schema each block answers to, so an error names the prop and what it must be.
const types = defs.Block.anyOf.map(({ $ref }) => defs[$ref.split("/").pop()].properties.type.const);
defs.Block = {
  description: defs.Block.description,
  type: "object",
  required: ["type"],
  properties: { type: { description: "What the block is; the other fields depend on it.", enum: types } },
  allOf: defs.Block.anyOf.map((ref, i) => ({ if: { properties: { type: { const: types[i] } } }, then: ref })),
};

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
