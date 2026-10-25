// A field for a number, in mm or with a unit the teacher types.
import { useLayoutEffect, useRef, useState } from "react";
import { round } from "../../arrange";

// The size of each unit in mm, for a length typed with one: 72 pt is an inch.
const UNITS: Record<string, number> = { mm: 1, cm: 10, pt: 25.4 / 72, in: 25.4 };

// What the field shows for a value: nothing where the blocks differ, else the number with a comma.
const text = (value?: number) => (value === undefined ? "" : String(round(value)).replace(".", ","));

// A field for a number. What is typed counts on Enter or when the field is left, and Escape drops it. An arrow up
// or down steps by one. `value` is absent where the selected blocks differ. With `units` a length may carry mm, cm,
// pt or in.
// The input is not controlled. WebKit's fill can write it before onChange, and a controlled field then paints the
// old value back over that text (#749). After a handle drag that redraw is the drag's size, so the typed 80 is
// lost (#793).
export function Num({ label, value, disabled, units, onCommit }: { label: string; value?: number; disabled: boolean; units?: boolean; onCommit: (n: number) => void }) {
  // Whether the mouse that is down brought the focus.
  const fresh = useRef(false);
  const input = useRef<HTMLInputElement>(null);
  // The text the sheet last asked the field to show.
  const shown = useRef(text(value));
  // The field set this value itself, by Enter or an arrow: the caret stays at the end of it.
  const own = useRef(false);
  // Escape, undo or a commit: the next draw shows the sheet, not what was typed over it.
  const follow = useRef(false);
  // Enter has committed. The blur that follows must not commit the same number again.
  const settled = useRef(false);
  // A commit whose number the sheet shows unchanged, as a percent does, still draws.
  const [pass, setPass] = useState(0);
  useLayoutEffect(() => {
    const el = input.current;
    if (!el) return;
    const next = text(value);
    const prev = shown.current;
    shown.current = next;
    const focused = document.activeElement === el;
    // What was typed stays, also when a drag's end lands late, after the first key (#727). A redraw keeps it too:
    // the text is in the DOM and nowhere else (#793). Not focused, the field follows the sheet.
    const typed = focused && !follow.current && el.value !== prev && el.value !== next;
    if (!typed && el.value !== next) {
      el.value = next;
      // The focus had selected the text. A new size from outside drops that selection, and the first key would
      // land behind it (#922). Selecting again puts the key in its place. A value the field set itself keeps the caret.
      if (focused && !own.current) el.select();
    }
    own.current = false;
    follow.current = false;
  }, [value, pass]);
  // Only digits with a comma or a point count: "1e3" and "Infinity" are numbers to JavaScript alone.
  const read = () => {
    const raw = input.current?.value.trim() ?? "";
    const unit = units && /^(-?\d+(?:[.,]\d+)?)\s*(mm|cm|pt|in)$/i.exec(raw);
    if (unit) return round(Number(unit[1].replace(",", ".")) * UNITS[unit[2].toLowerCase()]);
    return /^-?\d+([.,]\d+)?$/.test(raw) ? round(Number(raw.replace(",", "."))) : NaN;
  };
  const commit = (n: number) => {
    settled.current = true;
    const el = input.current;
    if (Number.isNaN(n) || n === value) {
      if (el) el.value = text(value);
      shown.current = text(value);
      return;
    }
    own.current = true;
    follow.current = true;
    onCommit(n);
    setPass((k) => k + 1);
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
        defaultValue={text(value)}
        onChange={() => (settled.current = false)}
        onFocus={(e) => {
          own.current = false;
          settled.current = false;
          e.target.select();
        }}
        // Safari puts the caret where the mouse comes up and so drops what the focus selected.
        onMouseDown={(e) => (fresh.current = document.activeElement !== e.target)}
        onMouseUp={(e) => {
          if (fresh.current) e.preventDefault();
          fresh.current = false;
        }}
        onBlur={() => {
          if (settled.current) {
            settled.current = false;
            return;
          }
          const el = input.current;
          if (el && el.value !== text(value)) commit(read());
        }}
        onKeyDown={(e) => {
          if (e.key === "Enter") commit(read());
          // Ctrl+Z and Ctrl+Y here undo and redo the sheet, whose step takes the place of what was typed.
          if (e.key === "Escape" || ((e.ctrlKey || e.metaKey) && /^[zy]$/i.test(e.key))) {
            follow.current = true;
            settled.current = true;
            setPass((k) => k + 1);
          }
          if (e.key !== "ArrowUp" && e.key !== "ArrowDown") return;
          e.preventDefault();
          const base = input.current && input.current.value !== text(value) ? read() : (value ?? NaN);
          commit(round(base + (e.key === "ArrowUp" ? 1 : -1)));
        }}
      />
    </label>
  );
}
