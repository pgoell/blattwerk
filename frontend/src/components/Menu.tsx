// The menu a right click opens: a modal dialog, so the keys are its own and the focus goes back where it was.
import { useLayoutEffect, useRef, type KeyboardEvent, type MouseEvent } from "react";
import type { LucideIcon } from "lucide-react";

// `on` is set for a command that is on or off, and marks the one that is on.
export type Item = { label: string; icon?: LucideIcon; keys?: string; disabled?: boolean; on?: boolean; run: () => void } | "sep";

// `up` puts the menu's bottom edge at `y`, for a menu that opens above its button.
// `tools` is a row of icon buttons over the blocks at `avoid`, which the row keeps clear of.
type Props = {
  x: number;
  y: number;
  up?: boolean;
  items: Item[];
  tools?: Exclude<Item, "sep">[];
  avoid?: { left: number; top: number; right: number; bottom: number };
  onClose: () => void;
  onElsewhere: (x: number, y: number) => void;
};

// The menu's own entries, which the arrows walk. The toolbar's buttons are not among them.
const ENTRY = "[role=menuitem]:enabled, [role=menuitemcheckbox]:enabled";

export default function Menu({ x, y, up, items, tools, avoid, onClose, onElsewhere }: Props) {
  const ref = useRef<HTMLDialogElement>(null);
  const row = useRef<HTMLDivElement>(null);
  useLayoutEffect(() => {
    const d = ref.current!;
    d.showModal();
    // Near the right or the bottom edge the menu moves back into the window.
    const box = d.getBoundingClientRect();
    d.style.left = `${Math.max(0, Math.min(x, innerWidth - box.width))}px`;
    d.style.top = `${Math.max(0, Math.min(up ? y - box.height : y, innerHeight - box.height))}px`;
    // The row goes 8 px above the blocks and the menu, or when there is no room above below them both, and stays
    // in the window.
    if (row.current && avoid) {
      const r = row.current.getBoundingClientRect();
      const menu = d.getBoundingClientRect();
      const above = Math.min(avoid.top, menu.top) - 8 - r.height;
      row.current.style.left = `${Math.max(0, Math.min(x, innerWidth - r.width))}px`;
      row.current.style.top = `${above >= 0 ? above : Math.min(Math.max(avoid.bottom, menu.bottom) + 8, innerHeight - r.height)}px`;
    }
    d.querySelector<HTMLElement>(ENTRY)?.focus();
  }, [x, y]);
  // Shuts the menu at once: the browser's `close` comes a task later, and until then the menu's button keeps the focus.
  const shut = () => {
    ref.current!.close();
    onClose();
  };
  // In a window of another size, as after a turn of the iPad, the menu's place is no longer right: it shuts.
  useLayoutEffect(() => {
    addEventListener("resize", shut);
    return () => removeEventListener("resize", shut);
  }, [onClose]);

  // Beside the menu is the dialog's backdrop: a press there has the dialog as its target and lies outside its box.
  const beside = (e: MouseEvent) => {
    const box = ref.current!.getBoundingClientRect();
    return e.target === ref.current && (e.clientX < box.left || e.clientX > box.right || e.clientY < box.top || e.clientY > box.bottom);
  };
  function key(e: KeyboardEvent) {
    // An Escape after the menu has shut is the sheet's.
    if (e.key === "Escape" && ref.current!.open) {
      e.preventDefault();
      e.stopPropagation();
      shut();
      return;
    }
    const step = { ArrowDown: 1, ArrowUp: -1 }[e.key];
    if (!step) return;
    e.preventDefault();
    const on = [...ref.current!.querySelectorAll<HTMLElement>(ENTRY)];
    on[(on.indexOf(document.activeElement as HTMLElement) + step + on.length) % on.length]?.focus();
  }
  // A command shuts the menu and its row at once, then runs.
  const pick = (item: Exclude<Item, "sep">) => {
    ref.current!.close();
    onClose();
    item.run();
  };
  return (
    <dialog
      ref={ref}
      className="menu"
      role="menu"
      onClose={onClose}
      onKeyDown={key}
      // The right button is the next line's: where it opens the menu on the press, both would run.
      onMouseDown={(e) => e.button !== 2 && beside(e) && shut()}
      onContextMenu={(e) => {
        e.preventDefault();
        if (beside(e)) onElsewhere(e.clientX, e.clientY);
      }}
    >
      {tools && (
        <div ref={row} role="toolbar" aria-label="Minisymbolleiste" className="mini">
          {tools.map((item) => (
            <button key={item.label} aria-label={item.label} title={item.label} disabled={item.disabled} onClick={() => pick(item)}>
              {item.icon && <item.icon size={16} aria-hidden />}
            </button>
          ))}
        </div>
      )}
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
            onClick={() => pick(item)}
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
