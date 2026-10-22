// The teacher sees the model's words beside her own and takes them, or she does not.
import { useEffect, useRef, useState } from "react";
import { post, type Refusal } from "../api";
import { SYMBOLS } from "../symbols";
import { levelled, NOTE, STAR, taken } from "../texthelp";
import type { Doc, TextBlock } from "../sheet";

type Kind = "simpler" | "shorter" | "levels";
type Proposal = { kind: "simpler" | "shorter"; text: string } | { kind: "levels"; texts: [string, string, string] };

const DOWN = "Die Texthilfe hat nicht geantwortet.";

export default function TextHelp({
  block,
  page,
  onClose,
  onTake,
}: {
  block: TextBlock;
  page: number;
  onClose: () => void;
  onTake: (fn: (doc: Doc) => Doc, to?: number) => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const field = useRef<HTMLTextAreaElement>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string>();
  const [proposal, setProposal] = useState<Proposal>();
  const [editing, setEditing] = useState(false);
  const [code, setCode] = useState(STAR);

  useEffect(() => {
    const dialog = ref.current;
    if (dialog && !dialog.open) dialog.showModal();
  }, []);

  async function ask(kind: Kind) {
    setBusy(true);
    setError(undefined);
    try {
      const got = await post<{ text?: string; texts?: string[] }>("/text/help", { text: block.props.text, kind });
      if (kind === "levels") {
        const texts = got.texts;
        if (!texts || texts.length !== 3) throw new Error("502");
        setProposal({ kind, texts: [texts[0], texts[1], texts[2]] });
      } else if (typeof got.text === "string") setProposal({ kind, text: got.text });
      else throw new Error("502");
    } catch (e) {
      setError((e as Refusal).detail ?? DOWN);
    } finally {
      setBusy(false);
    }
  }

  function levels(): [string, string, string] {
    const written = [...(ref.current?.querySelectorAll("textarea") ?? [])].map((el) => el.value);
    const texts = proposal?.kind === "levels" ? proposal.texts : (["", "", ""] as [string, string, string]);
    return [written[0] ?? texts[0], written[1] ?? texts[1], written[2] ?? texts[2]];
  }

  function take() {
    if (!proposal) return;
    if (proposal.kind === "levels") {
      const texts = editing ? levels() : proposal.texts;
      onTake((doc) => levelled(doc, page, block.id, texts, code, () => crypto.randomUUID()), page + 1);
      return;
    }
    const words = editing ? (field.current?.value ?? proposal.text) : proposal.text;
    onTake((doc) => ({
      ...doc,
      pages: doc.pages.map((p, i) =>
        i === page ? { ...p, blocks: p.blocks.map((b) => (b.id === block.id && b.type === "text" ? taken(b, words) : b)) } : p,
      ),
    }));
  }

  return (
    <dialog
      className="texthelp"
      ref={ref}
      aria-labelledby="texthelp-title"
      aria-busy={busy}
      onCancel={(e) => {
        e.preventDefault();
        onClose();
      }}
    >
      <h1 id="texthelp-title">Text anpassen</h1>
      {!proposal && (
        <div className="row">
          <button type="button" disabled={busy} onClick={() => ask("simpler")}>
            Einfacher
          </button>
          <button type="button" disabled={busy} onClick={() => ask("shorter")}>
            Kürzer
          </button>
          <button type="button" disabled={busy} onClick={() => ask("levels")}>
            In drei Niveaus
          </button>
        </div>
      )}
      {error && <p role="alert">{error}</p>}
      {proposal && (
        <p className="note" role="note">
          {NOTE}
        </p>
      )}
      {proposal && proposal.kind !== "levels" && (
        <div className="pair">
          <div>
            <h2>Bisher</h2>
            <p className="sample">{block.props.text}</p>
          </div>
          <div>
            <h2>Neu</h2>
            {editing ? <textarea ref={field} defaultValue={proposal.text} /> : <p className="sample">{proposal.text}</p>}
          </div>
        </div>
      )}
      {proposal?.kind === "levels" && (
        <>
          <div className="levels">
            {proposal.texts.map((words, i) => (
              <div key={i}>
                <h2>Niveau {i + 1}</h2>
                {editing ? <textarea ref={i === 0 ? field : undefined} defaultValue={words} /> : <p className="sample">{words}</p>}
              </div>
            ))}
          </div>
          <label>
            Zeichen
            <select value={code} onChange={(e) => setCode(e.target.value)}>
              {SYMBOLS.map(([value, name]) => (
                <option key={value} value={value}>
                  {name.split(",")[0]}
                </option>
              ))}
            </select>
          </label>
        </>
      )}
      {proposal && (
        <div className="row">
          <button type="button" onClick={() => setEditing(true)}>
            Bearbeiten
          </button>
          <button type="button" onClick={take}>
            Übernehmen
          </button>
          <button type="button" onClick={onClose}>
            Verwerfen
          </button>
        </div>
      )}
    </dialog>
  );
}
