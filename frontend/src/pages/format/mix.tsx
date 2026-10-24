// Schüttelwörter: the letters of each word in another order, for every selected text and shape.
import { draw, moves, type Shown } from "../../bank";
import { mixed, word } from "../../scramble";
import { boxed, holesOf, lineOf, shownParas, type TextProps } from "../../sheet";
import type { Block } from "../../sheet";
import { seedOf } from "./words";

// The words of a text that Schüttelwörter mixes, as typed and in reading order: a linked text has the sheet's words.
const sources = (p: TextProps, words: string[]) =>
  mixed(shownParas(p, words), { seed: 0 })
    .flat()
    .flatMap((part) => (part.source ? [part.source] : []));

// Schüttelwörter: the letters of each word in another order, for every selected text and shape. On unless all have a
// seed, as bold. Off keeps the settings stored, so the next press brings them back. "Neu schütteln" draws the best of
// 40 seeds, so in a long text a word can keep its order. A press that moves no word makes no step. A linked text with
// Lückenwörter is no mix: the gaps take its place.
export function Mix({ sel, look, words: sheet }: { sel: Block[]; look: (props: object, key?: string) => void; words: string[] }) {
  const held = sel.flatMap((b) => {
    const p = boxed(b);
    return p ? [p] : [];
  });
  if (!held.length) return null;
  const on = held.every((p) => seedOf(p.mix) !== undefined && !(p.list === true && holesOf(p)));
  const first = held.every((p) => p.mixFirst === true);
  const caps = held.every((p) => p.mixCaps === true);
  const linked = held.every((p) => p.list === true);
  const line = lineOf(held[0]);
  const lines = linked ? ([["after", "Linie dahinter"], ["under", "Linie darunter"]] as const) : ([[undefined, "Keine Linie"], ["after", "Linie dahinter"], ["under", "Linie darunter"]] as const);
  // One entry per word of each block, as the pupil sees it: in capitals where the caps are on.
  const words = (): Shown[] => held.flatMap((p) => sources(p, sheet).map((source) => ({ seed: seedOf(p.mix), show: (seed: number) => word(source, seed, p.mixFirst === true, p.mixCaps === true) })));
  return (
    <>
      <button className={on ? "on" : ""} aria-pressed={on} onClick={() => look(on ? { mix: undefined } : { mix: draw(), holes: undefined }, "mix")}>
        Schüttelwörter
      </button>
      {on && (
        <>
          <button className={first ? "on" : ""} aria-pressed={first} onClick={() => look({ mixFirst: first ? undefined : true }, "mixFirst")}>
            Erster Buchstabe bleibt
          </button>
          <button className={caps ? "on" : ""} aria-pressed={caps} onClick={() => look({ mixCaps: caps ? undefined : true }, "mixCaps")}>
            Großbuchstaben
          </button>
          <div className="seg">
            {lines.map(([value, label]) => (
              <button key={label} className={line === value ? "on" : ""} aria-pressed={line === value} onClick={() => look({ mixLine: value }, "mixLine")}>
                {label}
              </button>
            ))}
          </div>
          <button
            onClick={() => {
              const shown = words();
              const seed = draw(shown);
              if (moves(shown, seed)) look({ mix: seed }, "mixShuffle");
            }}
          >
            Neu schütteln
          </button>
        </>
      )}
    </>
  );
}
