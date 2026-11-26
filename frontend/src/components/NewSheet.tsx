// The chooser of "Neues Blatt": an empty sheet first, then every template with a picture of its first page.
import { memo, useEffect, useRef, useState } from "react";
import { Plus, X } from "lucide-react";
import { api } from "../api";
import type { Template } from "../pages/editor/palette";
import { ask, signed } from "../saves";
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
  // The teacher's own template goes after a question. One deleted on another device is gone as asked: a 404 is no
  // failure here. A failure is said in the chooser, which lies over the rest of the page; a session run out
  // brings the login instead.
  const [kept, setKept] = useState("");
  async function forget(t: Template) {
    if (!confirm(`Vorlage „${t.name}“ löschen?`)) return;
    setKept("");
    try {
      await signed(api(`/templates/${t.id}`, { method: "DELETE" })).catch((e: Error) => (e.message === "404" ? undefined : Promise.reject(e)));
      setTemplates((ts) => ts?.filter((o) => o.id !== t.id));
    } catch (e) {
      const why = (e as Error)?.message;
      if (why !== "401" && why !== "stale") setKept(t.name);
    }
  }
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
        {shown.map((t) =>
          t.id > 0 ? (
            // The teacher's own can be deleted here: the editor has no list of them.
            <div key={t.id} className="own">
              <button type="button" className="tile" aria-label={t.name} onClick={() => pick(t)}>
                <Picture t={t} />
                <span>{t.name}</span>
                <small>eigene Vorlage</small>
              </button>
              <button type="button" className="ib" aria-label={`Vorlage ${t.name} löschen`} title="Löschen" onClick={() => void forget(t)}>
                <X size={16} aria-hidden />
              </button>
            </div>
          ) : (
            <button key={t.id} type="button" className="tile" aria-label={t.name} onClick={() => pick(t)}>
              <Picture t={t} />
              <span>{t.name}</span>
            </button>
          ),
        )}
      </div>
      {!templates && !failed && <p className="lead" role="status">Vorlagen laden …</p>}
      {failed && <p className="lead" role="alert">Die Vorlagen konnten nicht geladen werden. Ein leeres Blatt geht trotzdem.</p>}
      {kept && <p className="lead" role="alert">Die Vorlage „{kept}“ konnte nicht gelöscht werden. Versuch es gleich noch einmal.</p>}
      {templates && filter === "Meine Vorlagen" && !shown.length && (
        <p className="lead">Noch keine eigene Vorlage. Im Editor wird aus einem Blatt eine Vorlage: rechts im Reiter „Blatt“.</p>
      )}
      <div className="row">
        <button type="button" className="plain" onClick={() => ref.current?.close()}>
          Abbrechen
        </button>
      </div>
    </dialog>
  );
}
