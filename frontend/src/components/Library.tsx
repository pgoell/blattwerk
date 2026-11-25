// The library "Mathe-Blöcke": a field over the sheet with a search box and, in groups, a card for each maths block
// with a small picture of it. A modal dialog as the menus are, so Escape and the focus are its own.
import { memo, useLayoutEffect, useRef, useState, type KeyboardEvent } from "react";
import { Search } from "lucide-react";
import type { Fresh } from "../insert";
import { found, type Entry } from "../pages/editor/library";
import { Paper, type Block, type Doc } from "../sheet";
import { beside } from "./useBackdrop";

// The room a picture has, in px.
const [ROOM_W, ROOM_H] = [128, 60];
// Every picture shows the block of this seed, so a card looks the same each time.
const SEED = 7;

// The block itself, drawn small on a page of its own size.
const Picture = memo(function Picture({ entry }: { entry: Entry }) {
  const fresh: Fresh = entry.make(SEED);
  const block = { id: "t", x: 0, y: 0, z: 0, locked: false, ...fresh } as Block;
  const doc: Doc = { pages: [{ blocks: [block] }], guides: { x: [], y: [] }, grid: 0 };
  const k = Math.min(ROOM_W / fresh.w, ROOM_H / fresh.h, 1.6);
  return (
    <span className="pic" aria-hidden style={{ width: fresh.w * k, height: fresh.h * k }}>
      <Paper doc={doc} k={k} />
    </span>
  );
});

// `up` puts the field's bottom edge at `y`, over a row of tools; without it the field's top is at `y`.
type Props = { x: number; y: number; up?: boolean; onPick: (fresh: (seed: number) => Fresh) => void; onClose: () => void };

export default function Library({ x, y, up, onPick, onClose }: Props) {
  const ref = useRef<HTMLDialogElement>(null);
  const [query, setQuery] = useState("");
  // The card the arrows are on, which Enter adds: a place in the cards that the search left.
  const [at, setAt] = useState(0);
  const groups = found(query);
  const cards = groups.flatMap((g) => g.entries);
  const on = cards[Math.min(at, cards.length - 1)];
  useLayoutEffect(() => {
    const d = ref.current!;
    d.showModal();
    const box = d.getBoundingClientRect();
    d.style.left = `${Math.max(8, Math.min(x, innerWidth - box.width - 8))}px`;
    d.style.top = `${Math.max(8, Math.min(up ? y - box.height : y, innerHeight - box.height - 8))}px`;
    d.querySelector("input")!.focus();
  }, [x, y]);
  const shut = () => {
    ref.current!.close();
    onClose();
  };
  // In a window of another size the field's place is no longer right: it shuts, as a menu does.
  useLayoutEffect(() => {
    addEventListener("resize", shut);
    return () => removeEventListener("resize", shut);
  }, [onClose]);
  const pick = (entry: Entry) => {
    shut();
    onPick(entry.make);
  };
  // The arrows walk the cards as they lie: left and right through all of them, up and down to the nearest card of
  // the row above or below.
  function key(e: KeyboardEvent) {
    if (e.key === "Escape" && ref.current!.open) {
      e.preventDefault();
      e.stopPropagation();
      shut();
      return;
    }
    if (e.key === "Enter" && e.target instanceof HTMLInputElement) {
      e.preventDefault();
      if (on) pick(on);
      return;
    }
    if (!["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown", "Home", "End"].includes(e.key) || !cards.length) return;
    // In the search box Home, End and the sideways arrows are the text's while there is text.
    if (query && ["ArrowLeft", "ArrowRight", "Home", "End"].includes(e.key)) return;
    e.preventDefault();
    const now = cards.indexOf(on);
    const els = [...ref.current!.querySelectorAll<HTMLElement>(".card")];
    let next = now;
    if (e.key === "ArrowRight") next = Math.min(now + 1, cards.length - 1);
    else if (e.key === "ArrowLeft") next = Math.max(now - 1, 0);
    else if (e.key === "Home") next = 0;
    else if (e.key === "End") next = cards.length - 1;
    else {
      const boxes = els.map((el) => el.getBoundingClientRect());
      const here = boxes[now];
      const down = e.key === "ArrowDown";
      // The rows beyond this one, the nearest first; in it the card closest sideways.
      const beyond = boxes.map((b, i) => ({ b, i })).filter(({ b }) => (down ? b.top > here.top + 1 : b.top < here.top - 1));
      if (beyond.length) {
        const row = down ? Math.min(...beyond.map(({ b }) => b.top)) : Math.max(...beyond.map(({ b }) => b.top));
        next = beyond.filter(({ b }) => Math.abs(b.top - row) < 1).sort((p, q) => Math.abs(p.b.left - here.left) - Math.abs(q.b.left - here.left))[0].i;
      }
    }
    setAt(next);
    els[next]?.scrollIntoView({ block: "nearest" });
  }
  return (
    <dialog
      ref={ref}
      className="library"
      aria-label="Mathe-Blöcke"
      onClose={onClose}
      onKeyDown={key}
      onMouseDown={(e) => beside(ref.current!, e) && shut()}
    >
      <label className="find">
        <Search size={15} aria-hidden />
        <input
          type="search"
          placeholder="Block suchen"
          aria-label="Block suchen"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setAt(0);
          }}
        />
      </label>
      <div className="shelf">
        {groups.map((g) => (
          <section key={g.name} aria-label={g.name}>
            <h3>{g.name}</h3>
            <div className="cards">
              {g.entries.map((entry) => (
                <button key={entry.label} type="button" className={entry === on ? "card on" : "card"} aria-label={entry.label} aria-current={entry === on || undefined} tabIndex={-1} onClick={() => pick(entry)}>
                  <Picture entry={entry} />
                  <span>{entry.label}</span>
                </button>
              ))}
            </div>
          </section>
        ))}
        {!cards.length && <p className="none" role="status">Kein Block passt zu „{query}“.</p>}
      </div>
    </dialog>
  );
}
