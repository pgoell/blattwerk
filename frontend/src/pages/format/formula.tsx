// The Formel panel: the source, a few templates, and the formula as it will print.
import { useState } from "react";
import { TEMPLATES, embed, sane, type FormulaProps } from "../../formula";
import { Formula } from "../../sheet/formulaView";
import type { FormulaBlock } from "../../sheet";

export function FormulaFields({ source, onChange }: { source: string; onChange: (source: string) => void }) {
  return (
    <>
      <label>
        Formel
        <input aria-label="Formel" value={source} onChange={(e) => onChange(e.target.value)} spellCheck={false} />
      </label>
      <div className="seg formula-gallery">
        {TEMPLATES.map((t) => (
          <button key={t.name} type="button" className={source === t.source ? "on" : ""} aria-label={t.name} aria-pressed={source === t.source} onClick={() => onChange(t.source)}>
            {t.name}
          </button>
        ))}
      </div>
      <div className="formula-preview" aria-label="Formelvorschau">
        <Formula source={source} />
      </div>
    </>
  );
}

export function FormulaPanel({ block, apply }: { block: FormulaBlock; apply: (props: Partial<FormulaProps>, key?: string) => void }) {
  const p = sane(block.props);
  return (
    <>
      <h2>Formel</h2>
      <FormulaFields source={p.source} onChange={(source) => apply({ source }, "source")} />
      <div className="seg">
        <button type="button" aria-label="Schrift kleiner" onClick={() => apply({ size: Math.max(8, p.size - 2) }, "size")}>−</button>
        <output>{p.size} pt</output>
        <button type="button" aria-label="Schrift größer" onClick={() => apply({ size: p.size + 2 }, "size")}>＋</button>
      </div>
    </>
  );
}

// Puts a formula into the text or the cell being written. The preview is the formula, not the marker.
export function FormulaInsert({ onInsert }: { onInsert: (text: string) => void }) {
  const [source, setSource] = useState<string>(TEMPLATES[0].source);
  return (
    <>
      <h2>Formel</h2>
      <FormulaFields source={source} onChange={setSource} />
      <button type="button" aria-label="Formel einfügen" onClick={() => onInsert(embed(source))}>
        Einfügen
      </button>
    </>
  );
}
