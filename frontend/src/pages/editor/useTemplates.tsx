// Saving the sheet as a template and applying one.
import { useRef } from "react";
import { api, post, type Refusal } from "../../api";
import { fresh } from "../../history";
import { attempt } from "../../fault";
import { signed } from "../../saves";
import { wordsIn, mathsHeight, read, sizeOf, type Block } from "../../sheet";
import { follow as growRulings } from "../../words";
import { made } from "../../zahlenmauer";
import { next } from "../../cells";
import { generate, newSeed } from "../Maths";
import type { Template } from "./palette";
import { usePrint } from "./usePrint";

export function useTemplates(session: ReturnType<typeof usePrint>) {
  const live = session.live;
  const setIds = session.setIds;
  const words = session.words;
  const setTemplates = session.setTemplates;
  const name = session.name;
  const setName = session.setName;
  const pages = session.pages;
  const blocks = session.blocks;
  const update = session.update;
  const turn = session.turn;
  const all = session.all;
// A template stored or deleted with the session run out brings the login. A second press while one is on its way
  // stores no second template. The name stays until the template is stored.
  const storing = useRef(false);
  async function store() {
    const made = { name: name.trim() };
    await attempt(
      "Die Vorlage konnte nicht gespeichert werden.",
      async () => {
        if (storing.current) return;
        storing.current = true;
        try {
          // The page as it stands at the try: a later one stores what the teacher sees then.
          const saved = await signed(post<Template>("/templates", { ...made, doc: live.current.doc }));
          setTemplates((ts) => [...ts, saved]);
          setName((now) => (now.trim() === made.name ? "" : now));
        } finally {
          storing.current = false;
        }
      },
      // A template the server refuses names what is wrong in it, and a try again would end the same.
      (_, e) => {
        const problems = (e as Refusal).problems;
        return problems ? `Die Vorlage konnte nicht gespeichert werden: das Blatt passt nicht zum Format. ${problems.join("; ")}` : undefined;
      },
    );
  }
  // A template takes the place of the sheet; undo brings the sheet back. A built-in one gets fresh seeds, and its
  // maths blocks fresh exercises from the server; a block whose request fails keeps its own. The sheet keeps its
  // Lernwörter unless the template brings some.
  // The last click wins: an apply still waiting for its exercises gives way to one started after it.
  const applied = useRef(0);
  async function apply(t: Template) {
    const turn = ++applied.current;
    const doc = read(t.doc);
    const pages = t.id > 0 ? doc.pages : await Promise.all(doc.pages.map(async (p) => ({
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
    if (turn !== applied.current) return;
    update((cur) => {
      const next = { ...doc, words: doc.words ?? cur.words };
      const words = wordsIn(next);
      const all = pages.flatMap((p) => p.blocks);
      return { ...next, pages: pages.map((p, n) => ({ ...p, blocks: growRulings(p.blocks, words, sizeOf(next, n)[0], sizeOf(next, n)[1], all) })) };
    });
    setIds([]);
  }
  async function forget(t: Template) {
    if (!confirm(`Vorlage „${t.name}“ löschen?`)) return;
    await attempt("Die Vorlage konnte nicht gelöscht werden.", async () => {
      // One deleted on another device is gone as asked: a 404 is no failure here.
      await signed(api(`/templates/${t.id}`, { method: "DELETE" })).catch((e: Error) => (e.message === "404" ? undefined : Promise.reject(e)));
      setTemplates((ts) => ts.filter((o) => o.id !== t.id));
    });
  }

    return Object.assign(session, { storing, store, applied, apply, forget });
}
