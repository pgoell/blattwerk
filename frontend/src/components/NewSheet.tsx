// The chooser of "Neues Blatt": an empty sheet first, then every template with a picture of its first page.
import { memo, useEffect, useRef, useState } from "react";
import { Plus } from "lucide-react";
import type { Template } from "../pages/editor/palette";
import { ask } from "../saves";
import { Paper, read, sizeOf } from "../sheet";
import { FILTERS, under, type Filter } from "../templates";
import { useBackdrop } from "./useBackdrop";

// The width of a card's picture, in px.
const WIDE = 132;

const Picture = memo(function Picture({ t }: { t: Template }) {
  const doc = read(t.doc);
  const [w, h] = sizeOf(doc, 0);
  // A page that lies on its side is as wide as the card and less high.
  return (
    <span className="pic" aria-hidden style={{ height: (WIDE * h) / w }}>
      <Paper doc={doc} k={WIDE / w} page={0} />
    </span>
  );
});

// `back` gives the button that opens the chooser as it stands now: the list draws that button anew once its sheets
// have come, and the one that was pressed is then no longer on the page to take the focus back.
type Props = { onPick: (t?: Template) => void; onClose: () => void; back?: () => HTMLElement | null };

export default function NewSheet({ onPick, onClose, back }: Props) {
  const ref = useRef<HTMLDialogElement>(null);
  const [templates, setTemplates] = useState<Template[]>();
  const [failed, setFailed] = useState(false);
  const [filter, setFilter] = useState<Filter>("Alle");
  useEffect(() => {
    const from = document.activeElement as HTMLElement | null;
    ref.current!.showModal();
    let on = true;
    ask<Template[]>("/templates").then(
      (all) => on && setTemplates(all),
      () => on && setFailed(true),
    );
    return () => {
      on = false;
      (from?.isConnected ? from : back?.())?.focus?.();
    };
  }, []);
  const backdrop = useBackdrop(ref);
  const shown = (templates ?? []).filter((t) => under(filter, t));
  const pick = (t?: Template) => {
    ref.current?.close();
    onPick(t);
  };
  return (
    <dialog ref={ref} className="chooser" aria-labelledby="chooser-title" onClose={onClose} {...backdrop}>
      <h1 id="chooser-title">Neues Blatt</h1>
      <div className="seg" role="group" aria-label="Vorlagen zeigen">
        {FILTERS.map((name) => (
          <button key={name} type="button" className={filter === name ? "on" : undefined} aria-pressed={filter === name} onClick={() => setFilter(name)}>
            {name}
          </button>
        ))}
      </div>
      <div className="shelf">
        {filter === "Alle" && (
          <button type="button" className="tile" aria-label="Leeres Blatt" onClick={() => pick()}>
            <span className="pic blank" aria-hidden>
              <Plus size={22} />
            </span>
            <span>Leeres Blatt</span>
          </button>
        )}
        {shown.map((t) => (
          <button key={t.id} type="button" className="tile" aria-label={t.name} onClick={() => pick(t)}>
            <Picture t={t} />
            <span>{t.name}</span>
            {t.id > 0 && <small>eigene Vorlage</small>}
          </button>
        ))}
      </div>
      {!templates && !failed && <p className="lead" role="status">Vorlagen laden …</p>}
      {failed && <p className="lead" role="alert">Die Vorlagen konnten nicht geladen werden. Ein leeres Blatt geht trotzdem.</p>}
      {templates && filter === "Meine Vorlagen" && !shown.length && (
        <p className="lead">Noch keine eigene Vorlage. Im Editor wird aus einem Blatt eine Vorlage: unter „Seiten und Vorlagen“.</p>
      )}
      <div className="row">
        <button type="button" className="plain" onClick={() => ref.current?.close()}>
          Abbrechen
        </button>
      </div>
    </dialog>
  );
}
