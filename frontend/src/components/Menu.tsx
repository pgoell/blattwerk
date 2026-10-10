// The menu a right click opens: a modal dialog, so the keys are its own and the focus goes back where it was.
import { useLayoutEffect, useRef, type KeyboardEvent, type MouseEvent } from "react";
import type { LucideIcon } from "lucide-react";

// `on` is set for a command that is on or off, and marks the one that is on.
export type Item = { label: string; icon?: LucideIcon; keys?: string; disabled?: boolean; on?: boolean; run: () => void } | "sep";

type Props = { x: number; y: number; items: Item[]; onClose: () => void; onElsewhere: (x: number, y: number) => void };

export default function Menu({ x, y, items, onClose, onElsewhere }: Props) {
  const ref = useRef<HTMLDialogElement>(null);
  useLayoutEffect(() => {
    const d = ref.current!;
    d.showModal();
    // Near the right or the bottom edge the menu moves back into the window.
    const box = d.getBoundingClientRect();
    d.style.left = `${Math.max(0, Math.min(x, innerWidth - box.width))}px`;
    d.style.top = `${Math.max(0, Math.min(y, innerHeight - box.height))}px`;
    d.querySelector<HTMLElement>("button:enabled")?.focus();
  }, [x, y]);
  // In a window of another size, as after a turn of the iPad, the menu's place is no longer right: it shuts.
  useLayoutEffect(() => {
    const shut = () => ref.current!.close();
    addEventListener("resize", shut);
    return () => removeEventListener("resize", shut);
  }, []);

  // Beside the menu is the dialog's backdrop: a press there has the dialog as its target and lies outside its box.
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
  return (
    <dialog
      ref={ref}
      className="menu"
      role="menu"
      onClose={onClose}
      onKeyDown={key}
      // The right button is the next line's: where it opens the menu on the press, both would run.
      onMouseDown={(e) => e.button !== 2 && beside(e) && ref.current!.close()}
      onContextMenu={(e) => {
        e.preventDefault();
        if (beside(e)) onElsewhere(e.clientX, e.clientY);
      }}
    >
      {items.map((item, i) =>
        item === "sep" ? (
          <hr key={i} />
        ) : (
          <button
            key={i}
            role={item.on === undefined ? "menuitem" : "menuitemcheckbox"}
            aria-label={item.label}
            aria-checked={item.on}
            disabled={item.disabled}
            onClick={() => {
              ref.current!.close();
              onClose();
              item.run();
            }}
          >
            {item.icon ? <item.icon size={14} aria-hidden /> : <i />}
            {item.label}
            {item.keys && <kbd>{item.keys}</kbd>}
          </button>
        ),
      )}
    </dialog>
  );
}
