// The Blattomat MCP server over stdio, with the key and address from the environment (BLATTWERK_TOKEN, BLATTWERK_URL).
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { connect } from "./api.ts";
import { build } from "./server.ts";

const token = (process.env.BLATTWERK_TOKEN ?? "").trim();
if (!token) {
  process.stderr.write("Blattomat: no API key set (BLATTWERK_TOKEN)\n");
  process.exit(1);
}
// The user may paste the address with a trailing slash or with /api at the end.
const base = (process.env.BLATTWERK_URL ?? "").trim() || "https://blattwerk.pgoell.com";
const url = base.replace(/\/+$/, "").replace(/\/api$/, "");

await build(connect(url, token)).connect(new StdioServerTransport());
