// The sheet's history, its title, and a newer copy saved in another window.
import { useEffect, useRef, useState } from "react";
import { NEWER } from "../../components/Variants";
import type { Hist } from "../../history";
import { drop as dropFault, note } from "../../fault";
import { newer, onNewer, owe, takeOwed, useSaves } from "../../saves";
import { lengthened, mathsHeight, overFoot, sizeOf, tall, type Block, type MathsProps, type Page } from "../../sheet";
import { made } from "../../zahlenmauer";
import { generate, kept as keptMaths } from "../Maths";
import type { Opened } from "./palette";
import { step } from "./palette";
import type { EditorProps } from "./props";

export function useDocument(session: EditorProps) {
  const file = session.file;
  const user = session.user;
  const renew = session.renew;
  const waiting = session.waiting;
  const change = (...a: any[]) => (session as Record<string, any>).change(...a);
  const lost = (...a: any[]) => (session as Record<string, any>).lost(...a);
  const turn = (...a: any[]) => (session as Record<string, any>).turn(...a);
  const pdf = (...a: any[]) => (session as Record<string, any>).pdf(...a);
// The saver has brought an old document up to date.
  const [hist, draw] = useState<Hist>(() => ({ past: [], doc: file.doc, future: [] }));
  // The text whose help dialog is open, and the page it stood on when she asked.
  const [help, setHelp] = useState<{ id: string; page: number } | null>(null);
  // The same as it stands after every change so far, drawn or not: a change knows at once what the one before left.
  const live = useRef(hist);
  const setHist = (step: (h: typeof hist) => typeof hist) => draw((live.current = step(live.current)));
  // A Lineatur on lines stored too short for its text grows to its rows once the fonts are in, as a Karo does on
  // load. No step to undo: the sheet opens so.
  useEffect(() => {
    document.fonts.ready.then(() =>
      setHist((h) => {
        const doc = lengthened(h.doc);
        return doc === h.doc ? h : { ...h, doc };
      }),
    );
  }, []);
  // Maths changes the session ran out on (saves.ts `owe`) are redone once the sheet opens after the login. The
  // clicks of one block go together, the later over the earlier, laid over the block as it is when the answer
  // comes: one request and one undo step a block. What cannot land says so.
  useEffect(() => {
    const changes = new Map<string, Partial<MathsProps>>();
    for (const { block, change } of takeOwed(file.id, user.id)) changes.set(block, { ...changes.get(block), ...change });
    const lost = "Eine Änderung an den Rechenaufgaben von vor der Anmeldung";
    const find = (block: string) => {
      const n = live.current.doc.pages.findIndex((p) => p.blocks.some((b) => b.id === block));
      const b = live.current.doc.pages[n]?.blocks.find((x) => x.id === block);
      return b?.type === "maths" ? { n, b } : undefined;
    };
    changes.forEach(async (change, block) => {
      const was = find(block);
      if (!was) return note("owed", `${lost} fand ihren Block nicht mehr und wurde nicht übernommen.`);
      const made = await generate({ ...was.b.props, ...change }).catch((e: Error) => e);
      // The session gone again keeps it owed with the red bar; another failure keeps it owed for the next opening.
      if (made instanceof Error) {
        owe(file.id, { block, change }, made.message === "401");
        if (made.message !== "401") note("owed", `${lost} konnte noch nicht übernommen werden. Öffne das Blatt später noch einmal.`);
        return;
      }
      const now = find(block);
      if (!now) return note("owed", `${lost} fand ihren Block nicht mehr und wurde nicht übernommen.`);
      const props = { ...now.b.props, ...change, ...keptMaths(now.b.props, { ...now.b.props, ...change }, made) };
      if (overFoot(now.b, props, sizeOf(live.current.doc, now.n)[1])) return note("owed", `${lost} passt nicht mehr auf die Seite und wurde nicht übernommen.`);
      turn((p: Page) => ({ ...p, blocks: p.blocks.map((x) => (x.id === block && x.type === "maths" ? ({ ...x, props, ...tall(x, mathsHeight(props)) } as Block) : x)) }), `owed ${block}`, now.n);
    });
  }, []);
  const [title, setTitle] = useState(file.title);
  // The sheet's saver: what the server holds, whether a save failed, and whether the server holds a newer document
  // than the one this editor is based on.
  const saver = useSaves().list.find((s) => s.id === file.id);
  const named = useRef(title);
  named.current = title;
  // Loads the newer sheet of another window, where this one has no change: it says so, and shows the sheet (#720).
  // With `variants` the new editor opens the print variants. A press asks anew, so the line of a load before goes.
  async function newerSheet(variants?: Opened) {
    const sheet = await newer(file.id, () => ({ doc: live.current.doc, title: named.current }));
    if (sheet) {
      note(NEWER, NEWER);
      renew(sheet, variants);
    }
    return !!sheet;
  }
  // The clash bar says it all then: no second red line.
  useEffect(() => void (saver?.clash && dropFault(NEWER)), [saver?.clash]);
  // A PDF pressed in the clash waits for the choice. It prints once the choice has ended, unless the sheet is gone.
  const [pdfWaits, setPdfWaits] = useState(waiting.current !== undefined);
  useEffect(() => {
    if (saver?.clash || waiting.current === undefined) return;
    const key = waiting.current;
    waiting.current = undefined;
    setPdfWaits(false);
    if (!saver?.gone) void pdf(key);
  }, [saver?.clash, saver?.gone]);
  // The dialog's state while it is open, so a newer sheet from another tab or a focus reopens it as it stands.
  const dialogState = useRef<Opened | undefined>(undefined);
  useEffect(() => onNewer(file.id, () => void newerSheet(dialogState.current)), []);
  useEffect(() => {
    const focus = () => void newerSheet(dialogState.current);
    addEventListener("focus", focus);
    return () => removeEventListener("focus", focus);
  }, []);
    return Object.assign(session, { hist, draw, help, setHelp, live, setHist, title, setTitle, saver, named, newerSheet, pdfWaits, setPdfWaits, dialogState });
}
