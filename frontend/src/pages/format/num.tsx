// A field for a number, in mm or with a unit the teacher types.
import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { round } from "../../arrange";

// The size of each unit in mm, for a length typed with one: 72 pt is an inch.
const UNITS: Record<string, number> = { mm: 1, cm: 10, pt: 25.4 / 72, in: 25.4 };

// A field for a number. What is typed counts on Enter or when the field is left, and Escape drops it. An arrow up
// or down steps by one. `value` is absent where the selected blocks differ. With `units` a length may carry mm, cm,
// pt or in.
export function Num({ label, value, disabled, units, onCommit }: { label: string; value?: number; disabled: boolean; units?: boolean; onCommit: (n: number) => void }) {
  const [draft, setDraft] = useState<string>();
  // Whether the mouse that is down brought the focus.
  const fresh = useRef(false);
  const input = useRef<HTMLInputElement>(null);
  // The field follows the sheet: a drag or an undo takes the place of what was typed. Not while the teacher types in
  // it: the end of a drag can land late, after the first key (#727), and Enter would then find nothing to set.
  useEffect(() => {
    if (document.activeElement !== input.current) setDraft(undefined);
  }, [value]);
  // The focus selected the text, and the drag's end that lands after it writes a new one, which drops the selection:
  // the first key would then go behind it, 9 cm after 69,14 making 691,49 (#922). Before the first key the text
  // stays all selected, as the focus left it. A value the field set itself, by Enter or an arrow, keeps the caret.
  const own = useRef(false);
  useLayoutEffect(() => {
    if (!own.current && document.activeElement === input.current && draft === undefined) input.current!.select();
    own.current = false;
  }, [value]);
  // Only digits with a comma or a point count: "1e3" and "Infinity" are numbers to JavaScript alone.
  const read = () => {
    const text = draft?.trim() ?? "";
    const unit = units && /^(-?\d+(?:[.,]\d+)?)\s*(mm|cm|pt|in)$/i.exec(text);
    if (unit) return round(Number(unit[1].replace(",", ".")) * UNITS[unit[2].toLowerCase()]);
    return /^-?\d+([.,]\d+)?$/.test(text) ? round(Number(text.replace(",", "."))) : NaN;
  };
  // Without a draft the blur that follows Enter finds nothing to set.
  const commit = (n: number) => {
    setDraft(undefined);
    if (Number.isNaN(n) || n === value) return;
    own.current = true;
    onCommit(n);
  };
  return (
    <label>
      {label}
      <input
        ref={input}
        className="mm"
        type="text"
        inputMode="decimal"
        disabled={disabled}
        value={draft ?? (value === undefined ? "" : String(round(value)).replace(".", ","))}
        onChange={(e) => setDraft(e.target.value)}
        onFocus={(e) => {
          own.current = false;
          e.target.select();
        }}
        // Safari puts the caret where the mouse comes up and so drops what the focus selected.
        onMouseDown={(e) => (fresh.current = document.activeElement !== e.target)}
        onMouseUp={(e) => {
          if (fresh.current) e.preventDefault();
          fresh.current = false;
        }}
        onBlur={() => draft !== undefined && commit(read())}
        onKeyDown={(e) => {
          if (e.key === "Enter") commit(read());
          // Ctrl+Z and Ctrl+Y here undo and redo the sheet, whose step takes the place of what was typed.
          if (e.key === "Escape" || ((e.ctrlKey || e.metaKey) && /^[zy]$/i.test(e.key))) setDraft(undefined);
          if (e.key !== "ArrowUp" && e.key !== "ArrowDown") return;
          e.preventDefault();
          commit(round((draft === undefined ? (value ?? NaN) : read()) + (e.key === "ArrowUp" ? 1 : -1)));
        }}
      />
    </label>
  );
}
