// A model may propose new words. Nothing here sends them: the editor asks, the teacher takes.
import { MARGIN, parasOf, sizeOf, stored, type Block, type Doc, type Para, type Run, type TextBlock } from "./sheet";
import { SYMBOLS } from "./symbols";

export const NOTE = "Ein Modell hat diesen Text geschrieben. Lies ihn, bevor du ihn druckst.";
export const STAR = "2B50";
const MARK = 8;
const GAP = 1;
const KNOWN = new Set(SYMBOLS.map(([code]) => code));

// The one text a teacher can ask about: her own words, not a list, not a locked block, not a shape.
export function canHelp(sel: Block[]): TextBlock | undefined {
  if (sel.length !== 1) return;
  const block = sel[0];
  if (block.type !== "text" || block.locked || block.props.list === true || !block.props.text.trim()) return;
  return block;
}

// A run's look, without the words and without a gap: a gap would hide the words she just took.
function lookOf(run: Run): Omit<Run, "text" | "gap"> {
  const { text: _text, gap: _gap, ...look } = run;
  return look;
}

// Each old run keeps its look for as many characters as it had. The last run takes whatever is left.
function carried(runs: Run[], line: string): Run[] {
  if (!line) return [];
  const usable = runs.filter((run) => run.text.length > 0);
  if (!usable.length) return [{ text: line }];
  const out: Run[] = [];
  let at = 0;
  for (let i = 0; i < usable.length && at < line.length; i++) {
    const last = i === usable.length - 1;
    const n = last ? line.length - at : Math.min(usable[i].text.length, line.length - at);
    out.push({ ...lookOf(usable[i]), text: line.slice(at, at + n) });
    at += n;
  }
  return out;
}

// The block with `next` as its words. Place, font, size and a paragraph's list stay.
export function taken(block: TextBlock, next: string): TextBlock {
  const old = parasOf(block.props);
  const paras: Para[] = next.split("\n").map((line, i) => {
    const was = old[i];
    const runs = carried(was?.runs ?? [], line);
    if (!was) return { runs };
    const { runs: _runs, ...rest } = was;
    return { ...rest, runs };
  });
  return { ...block, props: { ...block.props, ...stored(paras) } };
}

function copied(blocks: Block[], ids: () => string): { blocks: Block[]; idsOf: Map<string, string> } {
  const idsOf = new Map(blocks.map((b) => [b.id, ids()]));
  const groups = new Map<string, string>();
  const next = blocks.map((b) => {
    const group = b.group?.map((g) => groups.get(g) ?? groups.set(g, ids()).get(g)!);
    const copy = { ...b, id: idsOf.get(b.id)!, ...(group?.length ? { group } : {}) } as Block;
    if (!group?.length) delete copy.group;
    if (copy.type === "selbstkontrolle") {
      return { ...copy, props: { ...copy.props, links: copy.props.links.map((id) => idsOf.get(id) ?? id) } };
    }
    return copy;
  });
  return { blocks: next, idsOf };
}

function marks(count: number, code: string, width: number, z: number, ids: () => string): Block[] {
  const known = KNOWN.has(code) ? code : STAR;
  const row = count * MARK + (count - 1) * GAP;
  const x0 = Math.max(MARGIN, width - MARGIN - row);
  return Array.from({ length: count }, (_, i) => ({
    id: ids(),
    type: "symbol" as const,
    x: x0 + i * (MARK + GAP),
    y: MARGIN,
    w: MARK,
    h: MARK,
    z: z + 1 + i,
    locked: false,
    props: { code: known },
  }));
}

// The page stays. Three copies follow it, each with one version and one more of `code`.
export function levelled(
  doc: Doc,
  page: number,
  blockId: string,
  texts: readonly [string, string, string],
  code: string,
  ids: () => string,
): Doc {
  const source = doc.pages[page];
  const block = source?.blocks.find((b) => b.id === blockId);
  if (!source || block?.type !== "text") return doc;
  const [width] = sizeOf(doc, page);
  const copies = texts.map((words, i) => {
    const { blocks, idsOf } = copied(source.blocks, ids);
    const textId = idsOf.get(blockId)!;
    const withWords = blocks.map((b) => (b.id === textId && b.type === "text" ? taken(b, words) : b));
    const z = Math.max(0, ...withWords.map((b) => b.z));
    return { ...source, blocks: [...withWords, ...marks(i + 1, code, width, z, ids)] };
  });
  return { ...doc, pages: [...doc.pages.slice(0, page + 1), ...copies, ...doc.pages.slice(page + 1)] };
}
