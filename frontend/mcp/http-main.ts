// The Blattomat MCP server over HTTP, one stateless answer per request, for the remote route (src/blattwerk/remote.py).
// It listens on 127.0.0.1 and prints its port on the first line. It exits when its stdin closes.
import { createServer } from "node:http";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import { connect } from "./api.ts";
import { build } from "./server.ts";

const server = createServer(async (req, res) => {
  // Any throw in here, a client cut mid-body included, would end the child for every teacher: it answers this request only.
  try {
    if (req.method !== "POST" || req.url !== "/mcp") {
      res.writeHead(405, { Allow: "POST" }).end();
      return;
    }
    const chunks: Buffer[] = [];
    for await (const chunk of req) chunks.push(chunk as Buffer);
    let body: unknown;
    try {
      body = JSON.parse(Buffer.concat(chunks).toString("utf8"));
    } catch {
      // A body that is no JSON is only this request's fault.
      res.writeHead(400).end();
      return;
    }
    // The bearer token comes from the route, which checked it; the API address is set by the route too.
    const token = (req.headers.authorization ?? "").replace(/^Bearer /i, "");
    const api = String(req.headers["x-blattomat-api"] ?? "");
    const mcp = build(connect(api, token));
    const transport = new StreamableHTTPServerTransport({ sessionIdGenerator: undefined, enableJsonResponse: true });
    res.on("close", () => {
      transport.close();
      mcp.close();
    });
    await mcp.connect(transport);
    await transport.handleRequest(req, res, body);
  } catch {
    if (res.headersSent) res.destroy();
    else res.writeHead(500).end();
  }
});

server.listen(0, "127.0.0.1", () => {
  const address = server.address();
  process.stdout.write(`${JSON.stringify({ port: typeof address === "object" && address ? address.port : 0 })}\n`);
});

process.stdin.resume();
process.stdin.on("end", () => server.close(() => process.exit(0)));
