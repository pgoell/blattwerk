// The sheet's Lernwörter for a text or a shape: as its own text or as the list.
import { draw, moves } from "../../bank";
import { holed } from "../../holes";
import { boxed, holesOf, listColsOf, tied } from "../../sheet";
import type { Block, Doc } from "../../sheet";
import { WordList, type Listing } from "./wordlist";
import { seedOf } from "./words";
import { Switch } from "../../components/Switch";

// The sheet's Lernwörter for a text or a shape: as its own text or as the list, in 1 to 4 columns, with letters hidden as
// gaps in one of three ways. Each switch is on only when all the picked ones have it. "Neu wählen" picks the hidden letters anew, in "one" only: the other two modes do not depend on the seed.
export function Fed({ sel, words, doc, listing, look, link, feed }: { sel: Block[]; words: string[]; doc: Doc; listing: Listing; look: (props: object, key?: string) => void; link: (on: boolean) => void; feed: (props: object, key?: string) => void }) {
  const held = sel.flatMap((b) => {
    const p = boxed(b);
    return p ? [p] : [];
  });
  if (!held.length) return null;
  const linked = held.every((p) => p.list === true);
  const holes = held.every((p) => holesOf(p) !== undefined);
  const mode = holesOf(held[0]);
  const cols = listColsOf(held[0]);
  return (
    <>
      <h2>Wörter</h2>
      {/* The same switch as on a Lineatur: the block shows the sheet's list in place of a text of its own. Picked
          beside a Lineatur, each of the two says whose it is. */}
      <Switch label={sel.some((b) => b.type === "ruling") ? "Lernwörter des Blatts im Text" : "Lernwörter des Blatts"} on={linked} onChange={() => link(!linked)} />
      {linked && (
        <>
          {/* A picked Lineatur that shows the list has the field already. */}
          {!sel.some((b) => b.type === "ruling" && tied(b)) && <WordList doc={doc} listing={listing} />}
          <div className="seg">
            {[1, 2, 3, 4].map((n) => (
              <button key={n} className={cols === n ? "on" : ""} aria-label={n === 1 ? "1 Spalte" : `${n} Spalten`} aria-pressed={cols === n} onClick={() => look({ listCols: n === 1 ? undefined : n }, "listCols")}>
                {n}
              </button>
            ))}
          </div>
          <Switch label="Lückenwörter" on={holes} onChange={() => feed(holes ? { holes: undefined } : { holes: "one", holeSeed: seedOf(held[0].holeSeed) ?? draw(), mix: undefined }, "holes")} />
          {holes && mode && (
            <>
              <div className="seg">
                {([["one", "Ein Buchstabe"], ["second", "Jeder zweite"], ["vowels", "Alle Vokale"]] as const).map(([value, label]) => (
                  <button key={value} className={mode === value ? "on" : ""} aria-pressed={mode === value} onClick={() => feed({ holes: value }, "holesMode")}>
                    {label}
                  </button>
                ))}
              </div>
              {mode === "one" && (
                <button
                  onClick={() => {
                    const seed = seedOf(held[0].holeSeed);
                    const shown = words.map((w) => ({ seed, show: (s: number) => holed(w, mode, s).map((run) => (run.gap ? "_" : run.text)).join("") }));
                    const next = draw(shown);
                    if (moves(shown, next)) feed({ holeSeed: next }, "holesPick");
                  }}
                >
                  Neu wählen
                </button>
              )}
            </>
          )}
        </>
      )}
    </>
  );
}
