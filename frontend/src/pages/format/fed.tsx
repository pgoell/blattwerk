// The sheet's Lernwörter for a text or a shape: as its own text or as the list.
import { draw, moves } from "../../bank";
import { holed } from "../../holes";
import { boxed, holesOf, listColsOf } from "../../sheet";
import type { Block } from "../../sheet";
import { seedOf } from "./words";

// The sheet's Lernwörter for a text or a shape: as its own text or as the list, in 1 to 4 columns, with letters hidden as
// gaps in one of three ways. Each switch is on only when all the picked ones have it. "Neu wählen" picks the hidden letters anew, in "one" only: the other two modes do not depend on the seed.
export function Fed({ sel, words, toList, look, link, feed }: { sel: Block[]; words: string[]; toList: () => void; look: (props: object, key?: string) => void; link: (on: boolean) => void; feed: (props: object, key?: string) => void }) {
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
      <select aria-label="Text des Textfelds" value={linked ? "list" : "own"} onChange={(e) => link(e.target.value === "list")}>
        <option value="own">Eigener Text</option>
        <option value="list">Text aus Lernwörtern</option>
      </select>
      {linked && (
        <>
          <div className="seg">
            {[1, 2, 3, 4].map((n) => (
              <button key={n} className={cols === n ? "on" : ""} aria-label={n === 1 ? "1 Spalte" : `${n} Spalten`} aria-pressed={cols === n} onClick={() => look({ listCols: n === 1 ? undefined : n }, "listCols")}>
                {n}
              </button>
            ))}
          </div>
          <button onClick={toList}>Lernwörter bearbeiten</button>
          <button className={holes ? "on" : ""} aria-pressed={holes} onClick={() => feed(holes ? { holes: undefined } : { holes: "one", holeSeed: seedOf(held[0].holeSeed) ?? draw(), mix: undefined }, "holes")}>
            Lückenwörter
          </button>
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
