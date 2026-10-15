// The zoom's list, as PowerPoint's zoom dialog: a few percents and a field to type one. A modal dialog like the menus,
// so the keys are its own while it is open.
import { useLayoutEffect, useRef, type KeyboardEvent, type MouseEvent } from "react";

// `up` puts the list's bottom edge at `y`, for a list that opens above its button.
type Props = {
  x: number;
  y: number;
  up?: boolean;
  current: number;
  onPercent: (p: number) => void;
  onWidth: () => void;
  onFit: () => void;
  onClose: () => void;
};

const PERCENTS = [50, 75, 100, 150, 200];
// Digits with an optional decimal comma or point, and an optional percent sign.
const PERCENT = /^\s*(\d+(?:[.,]\d+)?)\s*%?\s*$/;

export default function ZoomList({ x, y, up, current, onPercent, onWidth, onFit, onClose }: Props) {
  const ref = useRef<HTMLDialogElement>(null);
  const field = useRef<HTMLInputElement>(null);
  useLayoutEffect(() => {
    const d = ref.current!;
    d.showModal();
    // Near the right or the bottom edge the list moves back into the window.
    const box = d.getBoundingClientRect();
    d.style.left = `${Math.max(0, Math.min(x, innerWidth - box.width))}px`;
    d.style.top = `${Math.max(0, Math.min(up ? y - box.height : y, innerHeight - box.height))}px`;
    field.current!.select();
  }, [x, y]);
  // In a window of another size the list's place is no longer right: it shuts.
  useLayoutEffect(() => {
    const shut = () => ref.current!.close();
    addEventListener("resize", shut);
    return () => removeEventListener("resize", shut);
  }, []);

  // Beside the list is the dialog's backdrop: a press there has the dialog as its target and lies outside its box.
  const beside = (e: MouseEvent) => {
    const box = ref.current!.getBoundingClientRect();
    return e.target === ref.current && (e.clientX < box.left || e.clientX > box.right || e.clientY < box.top || e.clientY > box.bottom);
  };
  function key(e: KeyboardEvent) {
    const step = { ArrowDown: 1, ArrowUp: -1 }[e.key];
    if (!step) return;
    e.preventDefault();
    const on = [...ref.current!.querySelectorAll<HTMLElement>("button:enabled")];
    on[(on.indexOf(document.activeElement as HTMLElement) + step + on.length) % on.length]?.focus();
  }
  // A wrong entry changes nothing: the field shows the current percent again, picked whole, for another try.
  function enter(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key !== "Enter") return;
    e.preventDefault();
    const m = PERCENT.exec(field.current!.value);
    const p = m ? parseFloat(m[1].replace(",", ".")) : 0;
    if (!(p > 0)) {
      field.current!.value = String(current);
      field.current!.select();
      return;
    }
    ref.current!.close();
    onPercent(p);
  }
  // A pick shuts the list first, so the focus goes back where it was.
  const pick = (run: () => void) => () => {
    ref.current!.close();
    run();
  };
  return (
    <dialog
      ref={ref}
      className="menu"
      role="menu"
      onClose={onClose}
      onKeyDown={key}
      onMouseDown={(e) => e.button !== 2 && beside(e) && ref.current!.close()}
    >
      {PERCENTS.map((p) => (
        <button key={p} role="menuitem" onClick={pick(() => onPercent(p))}>
          {p} %
        </button>
      ))}
      <button role="menuitem" onClick={pick(onWidth)}>
        Seitenbreite
      </button>
      <button role="menuitem" onClick={pick(onFit)}>
        Ganze Seite
      </button>
      <hr />
      <input ref={field} aria-label="Zoom in Prozent" defaultValue={current} inputMode="decimal" onKeyDown={enter} />
    </dialog>
  );
}
