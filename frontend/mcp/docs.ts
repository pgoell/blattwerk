// The docs bundle docs/okf/: its index is the server's instructions, and each .md file is a resource.
import { readFileSync, readdirSync } from "node:fs";
import { pathToFileURL } from "node:url";

// BLATTWERK_DOCS names another bundle folder (the tests use a copy); the default is the repo's.
const ROOT = process.env.BLATTWERK_DOCS
  ? pathToFileURL(`${process.env.BLATTWERK_DOCS}/`)
  : new URL("../../docs/okf/", import.meta.url);
const SCHEME = "blattomat://okf/";

export type Resource = { uri: string; name: string; title: string; description?: string; mimeType: string };

// The leading `key: value` lines between the first two `---` lines, quotes stripped.
function frontmatter(text: string): Record<string, string> {
  const lines = text.split("\n");
  const out: Record<string, string> = {};
  if (lines[0]?.trim() !== "---") return out;
  for (const line of lines.slice(1)) {
    if (line.trim() === "---") break;
    const match = /^([\w-]+):\s*(.*)$/.exec(line);
    if (match) out[match[1]] = match[2].trim().replace(/^(["'])(.*)\1$/, "$2");
  }
  return out;
}

function body(text: string): string {
  const lines = text.split("\n");
  if (lines[0]?.trim() !== "---") return text.trim();
  const end = lines.indexOf("---", 1);
  return end < 0 ? text.trim() : lines.slice(end + 1).join("\n").trim();
}

function pages(dir: URL, prefix = ""): string[] {
  return readdirSync(dir, { withFileTypes: true })
    .flatMap((entry) =>
      entry.isDirectory()
        ? pages(new URL(`${entry.name}/`, dir), `${prefix}${entry.name}/`)
        : entry.name.endsWith(".md")
          ? [`${prefix}${entry.name}`]
          : [],
    )
    .sort();
}

export const INSTRUCTIONS = body(readFileSync(new URL("index.md", ROOT), "utf8"));

export function resources(): Resource[] {
  return pages(ROOT).map((path) => {
    const meta = frontmatter(readFileSync(new URL(path, ROOT), "utf8"));
    const folder = path.includes("/") ? path.slice(0, path.lastIndexOf("/")) : "the bundle";
    const isIndex = path === "index.md" || path.endsWith("/index.md");
    const title = meta.title ?? (isIndex ? `Index of ${folder}` : path);
    const resource: Resource = { uri: SCHEME + path, name: path, title, mimeType: "text/markdown" };
    if (meta.description) resource.description = meta.description;
    return resource;
  });
}

export function readResource(uri: string) {
  const path = uri.startsWith(SCHEME) ? uri.slice(SCHEME.length) : "";
  const inside = path !== "" && !path.startsWith("/") && !path.split("/").includes("..");
  const known = inside && pages(ROOT).includes(path);
  if (!known) throw new Error(`No resource ${uri}. Call resources/list for the bundle's files.`);
  const text = readFileSync(new URL(path, ROOT), "utf8");
  return { contents: [{ uri, mimeType: "text/markdown", text }] };
}
