// The field a score is typed into.

import { useState, useRef, useEffect, type FocusEvent } from "react";

// A score as it is typed: a whole number from 1 to 999, or else none.
export const score = (text: string) => (/^\s*\d{1,3}\s*$/.test(text) && +text >= 1 ? +text : undefined);

// The field of a score, in a box or in the panel. However it ends, it keeps the typed score when that is a whole number
// from 1 to 999; any other text leaves the old one. On the sheet Escape keeps it too, as Enter does; in the panel (with
// `steps`) Escape gives up what was typed, as every panel number field does. `change` gets the score and makes no step
// when the sheet has it already. `end` runs after Enter, `blur` on leaving the field. `steps` adds the buttons that
// count by one, each from the sheet's own number, after the typed score is kept.
export function ScoreInput({ max, change, end, blur, steps }: { max: number; change: (max: number) => void; end?: () => void; blur?: (e: FocusEvent<HTMLInputElement>) => void; steps?: (by: number) => void }) {
  const [draft, setDraft] = useState(String(max));
  const [round, setRound] = useState(0);
  // What is typed, the score shown by the sheet, whether Escape ended the field, and whether the teacher typed in it.
  // A field nobody typed in sends nothing: in the panel its max is the first picked box's, and sending that would set
  // every picked box to it.
  const typed = useRef(String(max));
  const shown = useRef(max);
  const off = useRef(false);
  const dirty = useRef(false);
  const latest = useRef({ change, end, blur, steps });
  latest.current = { change, end, blur, steps };
  shown.current = max;
  // A press of a button counts too, though the first box's number may stay as it was: the field then shows the sheet's.
  useEffect(() => {
    typed.current = String(max);
    dirty.current = false;
    setDraft(String(max));
  }, [max, round]);
  // Runs on Enter, on a blur and when the field goes, so a score is kept once for each way the field ends.
  function keep() {
    if (off.current || !dirty.current) return;
    const next = score(typed.current);
    if (next === undefined) {
      typed.current = String(shown.current);
      return setDraft(typed.current);
    }
    dirty.current = false;
    latest.current.change(next);
  }
  // The field goes on the press that ends it, which takes no blur with it: so its score is kept as it leaves.
  useEffect(() => keep, []);
  function press(by: number) {
    keep();
    setRound((n) => n + 1);
    latest.current.steps?.(by);
  }
  return (
    <>
      {steps && <button aria-label="Ein Punkt weniger" onClick={() => press(-1)}>−</button>}
    <input
      className="score"
      inputMode="numeric"
      aria-label="Punkte"
      value={draft}
      onChange={(e) => {
        dirty.current = true;
        typed.current = e.target.value;
        setDraft(e.target.value);
      }}
      onFocus={() => (off.current = false)}
      onBlur={(e) => {
        keep();
        latest.current.blur?.(e);
      }}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === "F2") {
          // Enter is a choice, also of the number that stands there: several picked boxes all take it.
          dirty.current = true;
          keep();
          latest.current.end?.();
        }
        if (e.key !== "Escape") return;
        if (steps) {
          // What was typed is given up: a later visit of the field that types nothing sends nothing.
          off.current = true;
          dirty.current = false;
          typed.current = String(shown.current);
          setDraft(typed.current);
        } else {
          // The sheet keeps a valid score, as Enter does; the field then ends with no more to keep.
          dirty.current = true;
          keep();
          off.current = true;
        }
        e.currentTarget.blur();
      }}
    />
      {steps && <button aria-label="Ein Punkt mehr" onClick={() => press(1)}>＋</button>}
    </>
  );
}
