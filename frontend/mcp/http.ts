// The Blattomat MCP server over HTTP, for the remote route. Run: node frontend/mcp/http.ts.
import { register } from "node:module";

// The tools run the editor's modules, which load only through these hooks, so they register before the server loads.
register("./hooks.ts", import.meta.url);
await import("./http-main.ts");
