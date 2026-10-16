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

// The build writes its version in place of this placeholder (frontend/mcpb.mjs); the http bundle keeps it.
export const VERSION = "0.0.0-dev";
const RELOAD = "Bitte die Blattomat-Erweiterung neu laden: Konto, Erweiterung herunterladen.";

// `check`: the installed extension's fingerprint, and the one of the extension the app serves (null when it cannot tell).
export function build(api: Api, check?: { own: string; served: () => Promise<string | null> }): Server {
  const t = tools(api);
  const server = new Server(
    { name: "blattomat", version: VERSION },
    { capabilities: { tools: {}, resources: {} }, instructions: INSTRUCTIONS },
  );
  server.setRequestHandler(ListToolsRequestSchema, async () => ({ tools: t.list }));
  server.setRequestHandler(CallToolRequestSchema, async (req) => {
    const [result, served] = await Promise.all([
      t.call(req.params.name, req.params.arguments ?? {}),
      check ? check.served().catch(() => null) : null,
    ]);
    const old = typeof served === "string" && served !== check?.own;
    return old ? { ...result, content: [...result.content, { type: "text", text: RELOAD }] } : result;
  });
  server.setRequestHandler(ListResourcesRequestSchema, async () => ({ resources: resources() }));
  server.setRequestHandler(ReadResourceRequestSchema, async (req) => readResource(req.params.uri));
  return server;
}
