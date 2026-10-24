// The gaps of a Lückentext for every selected block that holds words.
import { useState } from "react";
import { allCellGap, allGap } from "../../gaps";
import { draw, moves, shuffled } from "../../bank";
import { K, boxed, parasOf, type Block } from "../../sheet";
import type { Picked } from "../Field";
import { Num } from "./num";
import { both, seedOf, solutions, worded } from "./words";

// The gaps of a Lückentext for every selected block that holds words: the switch of the gaps, the width they all
// have, the box of solution words, and every n-th word. Each switch is on unless all have it, as bold. With a table
// cell open the switch is that cell's, and with a text open that of the picked words.
export function Gaps({ sel, part, cell, look, style, gap, every }: { sel: Block[]; part?: Picked; cell?: number; look: (props: object, key?: string) => void; style: (type: Block["type"], props: object, key?: string, only?: string[]) => void; gap: (on: boolean) => void; every: (n: number) => void }) {
  const held = sel.filter(worded);
  // The n of "Jedes n-te Wort", as typed.
  const [n, setN] = useState("5");
  if (!held.length) return null;
  const cells = cell !== undefined && sel.length === 1 && sel[0].type === "table" ? sel[0].props : undefined;
  const lit = part ? !!part.gap : cells ? !!cells.gaps?.[Math.floor(cell! / cells.cols.length)]?.[cell! % cells.cols.length] : held.every((b) => (b.type === "table" ? allCellGap(b.props.cells, b.props.gaps) : allGap(parasOf(boxed(b)!))));
  const same = held.every((b) => worded(b)!.gapWidth !== undefined);
  const bank = held.every((b) => worded(b)!.bank !== undefined);
  const set = both(held, look, style);
  // The widest gap drawn in the selected blocks, in whole mm, or 30 when none is drawn.
  const widest = () => {
    const drawn = [...document.querySelectorAll<HTMLElement>(".block.sel .gap")];
    return drawn.length ? Math.max(5, Math.ceil(Math.max(...drawn.map((el) => el.offsetWidth / K)))) : 30;
  };
  // A linked text or shape has no gaps of its own, so only its width shows.
  const linked = held.every((b) => boxed(b)?.list === true);
  return (
    <>
      {!linked && (
        <button className={lit ? "on" : ""} aria-pressed={lit} onClick={() => gap(!lit)}>
          Lücke
        </button>
      )}
      <button className={same ? "on" : ""} aria-pressed={same} onClick={() => set({ gapWidth: same ? undefined : widest() }, "gapWidth")}>
        Lücken gleich breit
      </button>
      {same && <Num label="Breite der Lücken" value={worded(held[0])!.gapWidth} disabled={false} onCommit={(to) => set({ gapWidth: Math.max(5, to) }, "gapWidthTo")} />}
      {!linked && (
        <div className="seg">
          {/* The number stays in the panel until a button uses it: Ctrl+Z is the field's own. */}
          <input type="number" aria-label="n" className="own" min={2} step={1} value={n} onChange={(e) => setN(e.target.value)} />
          <button onClick={() => every(Math.max(2, Math.round(+n) || 2))}>Jedes n-te Wort</button>
        </div>
      )}
      {!linked && (
        <button className={bank ? "on" : ""} aria-pressed={bank} onClick={() => set({ bank: bank ? undefined : draw() }, "bank")}>
          Lösungswörter
        </button>
      )}
      {!linked && bank && (
        <button
          onClick={() => {
            const shown = held.map((b) => ({ seed: seedOf(worded(b)!.bank), show: (seed: number) => shuffled(solutions(b), seed, solutions(b)).join("\n") }));
            const seed = draw(shown);
            if (moves(shown, seed)) set({ bank: seed }, "shuffle");
          }}
        >
          Neu mischen
        </button>
      )}
    </>
  );
}
