import { readFileSync } from "node:fs";
import type { Api } from "./api.ts";

export const INSTRUCTIONS = readFileSync(new URL("./instructions.md", import.meta.url), "utf8");

export type ToolDef = { name: string; description: string; inputSchema: Record<string, unknown> };
export type ToolResult = { content: { type: string; text?: string; data?: string; mimeType?: string }[]; isError?: boolean };

export function tools(api: Api) {
  const list: ToolDef[] = [];
  async function call(name: string, args: any): Promise<ToolResult> {
    return { content: [{ type: "text", text: `unknown tool ${name} ${typeof api}${JSON.stringify(args)}` }], isError: true };
  }
  return { list, call };
}
