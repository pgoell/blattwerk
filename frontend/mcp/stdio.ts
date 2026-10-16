// The Blattomat MCP server over stdio. Run: node frontend/mcp/stdio.ts (env BLATTWERK_URL, BLATTWERK_TOKEN).
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { ListToolsRequestSchema, CallToolRequestSchema } from "@modelcontextprotocol/sdk/types.js";
import { register } from "node:module";
import { connect } from "./api.ts";

// The tools run the editor's modules, which load only through these hooks.
register("./hooks.ts", import.meta.url);
const { tools, INSTRUCTIONS } = await import("./tools.ts");

const token = process.env.BLATTWERK_TOKEN;
if (!token) {
  process.stderr.write("set BLATTWERK_TOKEN\n");
  process.exit(1);
}
const base = process.env.BLATTWERK_URL ?? "https://blattwerk.pgoell.com";
const t = tools(connect(base, token));

const server = new Server(
  { name: "blattomat", version: "0.1.0" },
  { capabilities: { tools: {} }, instructions: INSTRUCTIONS },
);
server.setRequestHandler(ListToolsRequestSchema, async () => ({ tools: t.list }));
server.setRequestHandler(CallToolRequestSchema, async (req) => t.call(req.params.name, req.params.arguments ?? {}));

await server.connect(new StdioServerTransport());
