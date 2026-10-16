// Builds the Claude Desktop extension: the MCP server in one bundled file, the docs, the manifest, packed by mcpb.
import { execFileSync } from "node:child_process";
import { cpSync, copyFileSync, mkdirSync, rmSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { build } from "rolldown";

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

cpSync(join(here, "../docs/okf"), join(stage, "okf"), { recursive: true });
copyFileSync(join(here, "mcp/manifest.json"), join(stage, "manifest.json"));

const mcpb = join(here, "node_modules/.bin/mcpb");
execFileSync(mcpb, ["validate", join(stage, "manifest.json")], { stdio: "inherit" });
execFileSync(mcpb, ["pack", stage, join(here, "../src/blattwerk/static/blattomat.mcpb")], { stdio: "inherit" });
