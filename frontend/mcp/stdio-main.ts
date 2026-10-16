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

// The app's version, for the line that asks to reload an old extension. Without an answer, no line.
const check = async (): Promise<string | null> => {
  try {
    const res = await fetch(`${url}/api/mcpb/version`, { signal: AbortSignal.timeout(2000) });
    if (res.status !== 200) return null;
    const version = (await res.json()).version;
    return typeof version === "string" ? version : null;
  } catch {
    return null;
  }
};

await build(connect(url, token), check).connect(new StdioServerTransport());
