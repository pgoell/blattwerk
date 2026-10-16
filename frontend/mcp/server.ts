// The Blattomat MCP server's wiring, shared by stdio-main.ts (one teacher's key, over stdio) and http-main.ts (the remote route).
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import {
  ListToolsRequestSchema,
  CallToolRequestSchema,
  ListResourcesRequestSchema,
  ReadResourceRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import type { Api } from "./api.ts";
import { INSTRUCTIONS, readResource, resources } from "./docs.ts";
import { tools } from "./tools.ts";

export function build(api: Api): Server {
  const t = tools(api);
  const server = new Server(
    { name: "blattomat", version: "0.1.0" },
    { capabilities: { tools: {}, resources: {} }, instructions: INSTRUCTIONS },
  );
  server.setRequestHandler(ListToolsRequestSchema, async () => ({ tools: t.list }));
  server.setRequestHandler(CallToolRequestSchema, async (req) => t.call(req.params.name, req.params.arguments ?? {}));
  server.setRequestHandler(ListResourcesRequestSchema, async () => ({ resources: resources() }));
  server.setRequestHandler(ReadResourceRequestSchema, async (req) => readResource(req.params.uri));
  return server;
}
