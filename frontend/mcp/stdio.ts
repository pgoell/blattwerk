// The Blattomat MCP server over stdio. Run: node frontend/mcp/stdio.ts (env BLATTWERK_URL, BLATTWERK_TOKEN).
import { register } from "node:module";

// The tools run the editor's modules, which load only through these hooks, so they register before the server loads.
register("./hooks.ts", import.meta.url);
await import("./server.ts");
