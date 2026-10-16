// The Blattomat MCP server's wiring, shared by stdio.ts (run from source) and bundle.ts (the .mcpb).
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  ListToolsRequestSchema,
  CallToolRequestSchema,
  ListResourcesRequestSchema,
  ReadResourceRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { connect } from "./api.ts";
import { INSTRUCTIONS, readResource, resources } from "./docs.ts";
import { tools } from "./tools.ts";

const token = (process.env.BLATTWERK_TOKEN ?? "").trim();
if (!token) {
  process.stderr.write("Blattomat: no API key set (BLATTWERK_TOKEN)\n");
  process.exit(1);
}
// The user may paste the address with a trailing slash or with /api at the end.
const base = (process.env.BLATTWERK_URL ?? "").trim() || "https://blattwerk.pgoell.com";
const url = base.replace(/\/+$/, "").replace(/\/api$/, "");
const t = tools(connect(url, token));

const server = new Server(
  { name: "blattomat", version: "0.1.0" },
  { capabilities: { tools: {}, resources: {} }, instructions: INSTRUCTIONS },
);
server.setRequestHandler(ListToolsRequestSchema, async () => ({ tools: t.list }));
server.setRequestHandler(CallToolRequestSchema, async (req) => t.call(req.params.name, req.params.arguments ?? {}));
server.setRequestHandler(ListResourcesRequestSchema, async () => ({ resources: resources() }));
server.setRequestHandler(ReadResourceRequestSchema, async (req) => readResource(req.params.uri));

await server.connect(new StdioServerTransport());
