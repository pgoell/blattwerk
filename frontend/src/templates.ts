// A template's pages as a sheet takes them: in the editor's panel and in the chooser of "Neues Blatt".
import { generate, newSeed } from "./pages/Maths";
import type { Template } from "./pages/editor/palette";
import { mathsHeight, read, type Block, type Doc } from "./sheet";
import { followDoc } from "./words";

// A built-in template gets fresh seeds, and its maths blocks fresh exercises from the server; a block whose request
// fails keeps its own. A template of the teacher's own stays as it was stored.
export async function pagesOf(t: Template): Promise<Doc["pages"]> {
  const doc = read(t.doc);
  if (t.id > 0) return doc.pages;
  return Promise.all(doc.pages.map(async (p) => ({
    ...p,
    blocks: await Promise.all(p.blocks.map(async (b): Promise<Block> => {
      const props = b.props as Record<string, unknown>;
      if (typeof props.seed !== "number") return b;
      const limits = { ...props, seed: newSeed() };
      if (b.type !== "maths") return { ...b, props: limits } as Block;
      const made = await generate(limits as Parameters<typeof generate>[0]).catch(() => undefined);
      if (!made) return b;
      // New exercises may need more room than the template's block: it grows, to the page's foot at most.
      const fresh = { ...limits, ...made };
      const h = Math.min(Math.max(b.h, mathsHeight(fresh as Parameters<typeof mathsHeight>[0])), 297 - b.y);
      return { ...b, h, props: fresh } as Block;
    })),
  })));
}

// The sheet a template starts: its pages, with what follows the Lernwörter laid out.
export async function sheetOf(t: Template): Promise<Doc> {
  return followDoc({ ...read(t.doc), pages: await pagesOf(t) });
}

// The filters of the chooser. A built-in template has an id below 0 and a group; the teacher's own have neither.
export const FILTERS = ["Alle", "Mathe", "Deutsch", "Meine Vorlagen"] as const;
export type Filter = (typeof FILTERS)[number];
export const under = (filter: Filter, t: Template) =>
  filter === "Alle" || (filter === "Meine Vorlagen" ? t.id > 0 : t.id < 0 && t.group === filter);
