// The three tabs of a block's settings: what it asks of the child, how it looks, where it lies.
import { useLayoutEffect, useRef, useState, type KeyboardEvent, type ReactNode } from "react";
import type { Block } from "../../sheet";

export const PANES = ["Aufgaben", "Aussehen", "Lage"] as const;
export type PaneName = (typeof PANES)[number];

// A stretch of the panel that belongs to one tab. The stylesheet hides what stands directly in a pane of another
// tab, so a pane may hold a pane of another tab; words must stand in an element, never bare in the pane.
export function Pane({ tab, children }: { tab: PaneName; children: ReactNode }) {
  return (
    <div className="pane" data-pane={tab}>
      {children}
    </div>
  );
}

// The blocks that set no task: their panel opens on Aussehen.
const LOOKS: Block["type"][] = ["text", "shape", "image", "symbol", "ruling"];
// The tab each kind of selection was left on, until the page is loaded again.
const left = new Map<string, PaneName>();
// The suite sets this: it reaches for a field of any tab right after a pick, so there the panel shows all three
// at once, one under the other, as it did before the tabs. The tests of the tabs themselves leave it unset.
const whole = () => (window as { wholePanel?: boolean }).wholePanel === true;

// Which tab the panel shows for what is picked, and which tabs have anything to show. `root` goes on the panel.
export function usePanes(sel: Block[]) {
  const root = useRef<HTMLElement>(null);
  const [has, setHas] = useState<PaneName[]>([...PANES]);
  const [, draw] = useState(0);
  const kind = [...new Set(sel.map((b) => b.type))].sort().join(" ");
  // After each draw: a tab none of whose panes holds anything is not offered.
  useLayoutEffect(() => {
    const el = root.current;
    if (!el || !sel.length) return;
    const now = PANES.filter((p) => el.querySelector(`.pane[data-pane=${p}] > :not(.pane)`));
    if (now.join() !== has.join()) setHas(now);
  });
  if (whole() || !sel.length) return { root, has: [], open: undefined, pick: () => {} };
  const first: PaneName = sel.every((b) => LOOKS.includes(b.type)) ? "Aussehen" : "Aufgaben";
  const want = left.get(kind) ?? first;
  const open = has.includes(want) ? want : has.includes(first) ? first : has.includes("Aussehen") ? "Aussehen" : has[0];
  const pick = (to: PaneName) => {
    left.set(kind, to);
    draw((n) => n + 1);
  };
  return { root, has, open, pick };
}

// The row of tabs. The arrow keys walk it and take the focus along, Home and End jump to its ends.
export function PaneTabs({ has, open, pick }: { has: PaneName[]; open?: PaneName; pick: (to: PaneName) => void }) {
  if (!open || has.length < 2) return null;
  const walk = (e: KeyboardEvent<HTMLDivElement>) => {
    const by = { ArrowRight: 1, ArrowLeft: -1, Home: -has.length, End: has.length }[e.key];
    if (!by) return;
    e.preventDefault();
    e.stopPropagation();
    const to = has[Math.max(0, Math.min(has.length - 1, Math.abs(by) > 1 ? (by > 0 ? has.length - 1 : 0) : (has.indexOf(open) + by + has.length) % has.length))];
    pick(to);
    e.currentTarget.querySelector<HTMLElement>(`[data-tab=${to}]`)?.focus();
  };
  return (
    <div className="tabs panes" role="tablist" aria-label="Einstellungen" onKeyDown={walk}>
      {has.map((p) => (
        <button key={p} role="tab" data-tab={p} aria-selected={open === p} tabIndex={open === p ? 0 : -1} onClick={() => pick(p)}>
          {p}
        </button>
      ))}
    </div>
  );
}
