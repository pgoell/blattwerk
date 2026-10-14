// The format panel's settings for a Selbstkontrolle block: its heading, form, Lösungswort, size and turn, and the
// maths blocks of the sheet that it checks.
import { useState } from "react";
import type { Block, Box, Doc } from "../sheet";
import { checked, labelOf, ordered, sane, tasksOf, worded, type SelbstkontrolleProps } from "../selbstkontrolle";
import { newSeed } from "./Maths";

// Until sheet.tsx lists the block in its union, the block is declared here.
export type SelbstkontrolleBlock = Box & { type: "selbstkontrolle"; props: SelbstkontrolleProps };

type Apply = (props: Partial<SelbstkontrolleProps>, key?: string) => void;

// A whole number in a field. The field keeps its draft while the number is one `ok` would not take.
function Size({ value, apply }: { value: number; apply: Apply }) {
  const [draft, setDraft] = useState<string | null>(null);
  return (
    <label>
      Schriftgröße
      <input
        type="number"
        inputMode="numeric"
        aria-label="Schriftgröße"
        value={draft ?? String(value)}
        onChange={(e) => {
          const text = e.target.value;
          setDraft(text);
          if (/^\d+$/.test(text) && Number(text) >= 8 && Number(text) <= 24) apply({ size: Number(text) }, "size");
        }}
        onBlur={() => setDraft(null)}
      />
    </label>
  );
}

export default function Selbstkontrolle({ block, doc, apply }: { block: SelbstkontrolleBlock; doc: Doc; apply: Apply }) {
  const p = sane(block.props);
  const { fault, lost } = checked(p, doc);
  const ids = doc.pages.flatMap((page) => page.blocks).filter((b) => tasksOf(b) !== undefined).map((b) => b.id);
  const maths = ordered(doc, ids);
  const paged = doc.pages.length > 1;
  const pageOf = (b: Block) => doc.pages.findIndex((page) => page.blocks.some((x) => x.id === b.id)) + 1;
  // One step per tick: a link goes on or off, and the order the teacher ticked stays.
  const toggle = (id: string) => apply({ links: p.links.includes(id) ? p.links.filter((x) => x !== id) : [...p.links, id] });

  return (
    <>
      <h2>Selbstkontrolle</h2>
      <label>
        Überschrift
        <input type="text" aria-label="Überschrift" value={p.title} onChange={(e) => apply({ title: e.target.value }, "title")} />
      </label>
      <select aria-label="Form" value={p.form} onChange={(e) => apply({ form: e.target.value as SelbstkontrolleProps["form"] })}>
        <option value="mixed">Lösungen durcheinander</option>
        <option value="word">Lösungswort</option>
        <option value="sum">Kontrollsumme</option>
      </select>
      {p.form === "word" && (
        <label>
          Lösungswort
          <input type="text" aria-label="Lösungswort" value={p.word} onChange={(e) => apply({ word: e.target.value }, "word")} />
        </label>
      )}
      <Size value={p.size} apply={apply} />
      <select aria-label="Drucken" value={p.turn} onChange={(e) => apply({ turn: e.target.value as SelbstkontrolleProps["turn"] })}>
        <option value="none">Normal</option>
        <option value="upside">Auf dem Kopf</option>
        <option value="fold">Mit Knicklinie</option>
      </select>
      {p.form !== "sum" && (
        <button className="wide" onClick={() => apply({ seed: newSeed() })}>
          Neu mischen
        </button>
      )}
      <h2>Blöcke</h2>
      {lost.map((id) => (
        <label key={id}>
          <input type="checkbox" checked onChange={() => toggle(id)} />
          Gelöschter Block
        </label>
      ))}
      {maths.map((b) => (
        <label key={b.id}>
          <input type="checkbox" checked={p.links.includes(b.id)} onChange={() => toggle(b.id)} />
          {labelOf(b, doc)}
          {paged && ` (Seite ${pageOf(b)})`}
          {p.form === "word" && !worded(b) && <span className="hint"> (nicht im Lösungswort)</span>}
        </label>
      ))}
      {fault && (
        <p className="hint warn" role="status">
          {fault}
        </p>
      )}
    </>
  );
}
