// Builds the Claude Desktop extension: the MCP server in one bundled file, the docs, the manifest, packed by mcpb.
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { cpSync, mkdirSync, readdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { build } from "rolldown";

const PLACEHOLDER = '"0.0.0-dev"';

// Every file under a folder, by its path with "/" between the folders.
function filesIn(dir, prefix = "") {
  return readdirSync(join(dir, prefix), { withFileTypes: true }).flatMap((entry) =>
    entry.isDirectory() ? filesIn(dir, `${prefix}${entry.name}/`) : [`${prefix}${entry.name}`],
  );
}

const here = fileURLToPath(new URL(".", import.meta.url));
const stage = join(here, ".mcpb-stage");
rmSync(stage, { recursive: true, force: true });
mkdirSync(join(stage, "server"), { recursive: true });

await build({
  input: join(here, "mcp/bundle.ts"),
  platform: "node",
  transform: { jsx: "react-jsx" },
  // .mjs: Node before 22 reads a .js file with no package.json beside it as CommonJS.
  output: { file: join(stage, "server/index.mjs"), format: "esm", codeSplitting: false },
});

// The remote route's child (src/blattwerk/remote.py), in the image as /app/mcp/http.mjs.
await build({
  input: join(here, "mcp/http-main.ts"),
  platform: "node",
  transform: { jsx: "react-jsx" },
  output: { file: join(here, ".mcp-http/http.mjs"), format: "esm", codeSplitting: false },
});

cpSync(join(here, "../docs/okf"), join(stage, "okf"), { recursive: true });

// The version is a hash of what the extension is made of, so any change to it makes a new one.
const indexPath = join(stage, "server/index.mjs");
const indexText = readFileSync(indexPath, "utf8");
const sourcePath = join(here, "mcp/manifest.json");
const sourceText = readFileSync(sourcePath, "utf8");
// Every copy: the bundler may inline the constant into a comparison as well as its declaration.
if (!indexText.includes(PLACEHOLDER)) throw new Error(`${PLACEHOLDER} is not in the bundle`);
const hash = createHash("sha256").update(indexText);
for (const rel of filesIn(join(stage, "okf")).sort()) {
  hash.update(rel).update(readFileSync(join(stage, "okf", rel)));
}
hash.update(sourceText);
const version = `0.1.${parseInt(hash.digest("hex").slice(0, 8), 16)}`;

writeFileSync(indexPath, indexText.replaceAll(PLACEHOLDER, `"${version}"`));
const { manifest_version, ...manifest } = JSON.parse(sourceText);
writeFileSync(join(stage, "manifest.json"), `${JSON.stringify({ manifest_version, version, ...manifest }, null, 2)}\n`);

const mcpb = join(here, "node_modules/.bin/mcpb");
execFileSync(mcpb, ["validate", join(stage, "manifest.json")], { stdio: "inherit" });
execFileSync(mcpb, ["pack", stage, join(here, "../src/blattwerk/static/blattomat.mcpb")], { stdio: "inherit" });
