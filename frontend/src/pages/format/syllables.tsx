// The bows under the syllables and their colours, and a word's breaks mended by hand.
import { Fragment, useEffect, useState } from "react";
import { GREYS, TINTS, listOf, pairOf, useSplitter, type Block, type Doc } from "../../sheet";
import type { Picked } from "../Field";
import { both, syllabled } from "./words";

// The switches for the bows under the syllables and for their colours, for every selected block that holds words: on
// unless all have them, as bold. With Silbenfarbe on, the pair and the choices for it stand below. With one such block
// its words stand below too, each as it is split, to mend by hand: a click on a word shows its letters, and a click
// between two of them sets a break there or takes it away.
export function Syllables({ sel, part, look, style, mendWord, doc, words }: { sel: Block[]; part?: Picked; look: (props: object, key?: string) => void; style: (type: Block["type"], props: object, key?: string, only?: string[]) => void; mendWord: (keys: string[], counts: number[] | undefined, id: string) => void; doc: Doc; words: string[] }) {
  const held = sel.filter(syllabled);
  const bowsOn = held.every((b) => syllabled(b)!.syllables);
  // A stored pair that is garbage colours nothing, so the switch is off for it.
  const tintsOn = held.every((b) => pairOf(syllabled(b)!.tints));
  const pair = pairOf(held[0] && syllabled(held[0])!.tints) ?? TINTS;
  const greys = pair[0] === GREYS[0] && pair[1] === GREYS[1];
  const across = held.every((b) => syllabled(b)!.tintsAcross);
  const split = useSplitter(bowsOn || tintsOn);
  // The word whose letters show, as `breaks` names it.
  const [open, setOpen] = useState<string>();
  // The word the caret stands in opens with no click.
  useEffect(() => {
    if (split && part?.word) setOpen(split.keyOf(part.word));
  }, [split, part?.word]);
  const set = both(held, look, style);
  const one = split && held.length === 1 ? syllabled(held[0])! : undefined;
  const fixes = { ...doc.breaks, ...one?.breaks };
  // Whether the teacher split the word, under its key or under the old one: "constructor" is a word too, and every object has one.
  const own = (w?: string) => !!w && [split!.keyOf(w), split!.oldKeyOf(w)].some((key) => Object.hasOwn(fixes, key) && Array.isArray(fixes[key]));
  // Each word once, however it is written: a split holds for "Abend" and "abend" alike.
  const keys = new Set<string>();
  // A Lineatur on the Lernwörter list has the sheet's words, not a text of its own.
  const linked = !!one && held[0].type === "ruling" && listOf(held[0]) !== undefined;
  const all = one ? split!.words(linked ? words.join("\n") : "cells" in one ? one.cells.flat().join("\n") : one.text ?? "").filter((w) => !keys.has(split!.keyOf(w)) && keys.add(split!.keyOf(w))) : [];
  const word = all.find((w) => split!.keyOf(w) === open);
  // Sets or removes the break at `at`, or with none takes the word back to its own split. A word split as the
  // module splits it needs no entry. The mend holds for the word in every block of the sheet.
  const mend = (at?: number) => {
    const now = split!.cuts(word!, fixes);
    const next = at === undefined ? undefined : now.includes(at) ? now.filter((cut) => cut !== at) : [...now, at].sort((a, b) => a - b);
    const counts = next && split!.counted(word!, next);
    mendWord([split!.keyOf(word!), split!.oldKeyOf(word!)], counts && String(counts) !== String(split!.counted(word!, split!.split(word!))) ? counts : undefined, held[0].id);
  };
  return (
    <>
      {/* Off is no entry, as on a sheet that never had bows. */}
      <button className={bowsOn ? "on" : ""} aria-pressed={bowsOn} onClick={() => set({ syllables: bowsOn ? undefined : true }, "syllables")}>
        Silbenbögen
      </button>
      <button className={tintsOn ? "on" : ""} aria-pressed={tintsOn} onClick={() => set(tintsOn ? { tints: undefined, tintsAcross: undefined } : { tints: TINTS }, "tints")}>
        Silbenfarbe
      </button>
      {tintsOn && (
        <>
          <label>
            Erste Silbe
            <input type="color" value={pair[0]} onChange={(e) => set({ tints: [e.target.value, pair[1]] }, "tint0")} />
          </label>
          <label>
            Zweite Silbe
            <input type="color" value={pair[1]} onChange={(e) => set({ tints: [pair[0], e.target.value] }, "tint1")} />
          </label>
          <button className={greys ? "on" : ""} aria-pressed={greys} onClick={() => set({ tints: greys ? TINTS : GREYS }, "tints")}>
            Schwarz/Grau
          </button>
          <button className={across ? "on" : ""} aria-pressed={across} onClick={() => set({ tintsAcross: across ? undefined : true })}>
            Über Wortgrenzen
          </button>
        </>
      )}
      {one && all.length > 0 && (
        <>
          <p className="hint">Silbe falsch? Wort anklicken und Trennstellen setzen.</p>
          <div className="words">
            {all.map((w) => {
              const key = split!.keyOf(w);
              const cut = [0, ...split!.cuts(w, fixes), w.length];
              return (
                <button key={key} className={`${key === open ? "on" : ""}${own(w) ? " own" : ""}`} aria-pressed={key === open} title={own(w) ? "von Hand getrennt" : undefined} onClick={() => setOpen(key)}>
                  {cut.slice(1).map((end, i) => w.slice(cut[i], end)).join("·")}
                </button>
              );
            })}
          </div>
          {word && (
            <div className="gaps">
              {word.split("").map((letter, i) => {
                const cut = split!.cuts(word, fixes).includes(i);
                return (
                  <Fragment key={i}>
                    {/* No break before a mark that belongs to the letter before it. */}
                    {i > 0 && !/\p{M}/u.test(letter) && (
                      <button className={cut ? "on" : ""} aria-label={`${word.slice(0, i)}|${word.slice(i)}`} aria-pressed={cut} onClick={() => mend(i)}>
                        {cut ? "|" : "·"}
                      </button>
                    )}
                    {letter}
                  </Fragment>
                );
              })}
            </div>
          )}
          {word && own(word) && <button onClick={() => mend()}>Zurücksetzen</button>}
        </>
      )}
    </>
  );
}
