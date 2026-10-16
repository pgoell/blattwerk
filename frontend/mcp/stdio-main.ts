// The Blattomat MCP server over stdio, with the key and address from the environment (BLATTWERK_TOKEN, BLATTWERK_URL).
import { readFileSync } from "node:fs";
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

// The fingerprint the build put beside the bundle (frontend/mcpb.mjs). Run from source there is none, and no check.
let own: string | undefined;
try {
  own = readFileSync(new URL("../fingerprint.txt", import.meta.url), "utf8").trim();
} catch {}

// The fingerprint of the extension the app serves, for the line that asks to reload an old one. Without an answer, no line.
const served = async (): Promise<string | null> => {
  try {
    const res = await fetch(`${url}/api/mcpb/version`, { signal: AbortSignal.timeout(2000) });
    if (res.status !== 200) return null;
    const fingerprint = (await res.json()).fingerprint;
    return typeof fingerprint === "string" ? fingerprint : null;
  } catch {
    return null;
  }
};

await build(connect(url, token), own ? { own, served } : undefined).connect(new StdioServerTransport());
