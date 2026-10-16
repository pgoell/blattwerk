// Lets Node load the editor's own modules (frontend/src) as Vite does: an import without an extension finds its .ts
// or .tsx file, and a .tsx file is turned into JavaScript. The server then runs the editor's code, never a copy.
import { transformSync } from "rolldown/utils";
import { existsSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

type Next = (spec: string, ctx: any) => any;

export async function resolve(spec: string, ctx: { parentURL?: string }, next: Next) {
  if (spec.startsWith(".") && ctx.parentURL?.startsWith("file:") && !/\.\w+$/.test(spec)) {
    for (const ext of [".ts", ".tsx"]) {
      if (existsSync(fileURLToPath(new URL(spec + ext, ctx.parentURL)))) return next(spec + ext, ctx);
    }
  }
  return next(spec, ctx);
}

export async function load(url: string, ctx: unknown, next: Next) {
  if (!url.endsWith(".tsx")) return next(url, ctx);
  const path = fileURLToPath(url);
  const { code } = transformSync(path, readFileSync(path, "utf8"), { jsx: { runtime: "automatic" } });
  return { format: "module", source: code, shortCircuit: true };
}
