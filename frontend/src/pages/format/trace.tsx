// The trace text of a text, a shape, a table or a Lineatur: Aus, Grau, Umriss or Gepunktet.
import { dottedFamily, fadeOf, traceOf, type Fade, type Font } from "../../sheet";

// The trace text of a text, a shape, a table or a Lineatur: Aus, Grau, Umriss or Gepunktet. Gepunktet needs the font's
// dotted cut. Fading makes the trace lighter along the row or from row to row. Aus takes the fading along; the other
// choices set only their own keys.
const TRACE_CHOICE: Record<string, { trace?: true | "outline" | "dotted"; fade?: Fade }> = {
  off: { trace: undefined, fade: undefined },
  grey: { trace: true },
  outline: { trace: "outline" },
  dotted: { trace: "dotted" },
};
export function TraceControls({ props, font, onChange }: { props: { trace?: unknown; fade?: unknown; font?: Font }; font: Font | undefined; onChange: (props: { trace?: true | "outline" | "dotted"; fade?: Fade }) => void }) {
  const trace = traceOf({ ...props, font }) ?? "off";
  const fade = fadeOf({ ...props, font });
  const dotted = !!dottedFamily(font);
  return (
    <>
      <select aria-label="Nachspurtext" value={trace} onChange={(e) => onChange(TRACE_CHOICE[e.target.value])}>
        <option value="off">Aus</option>
        <option value="grey">Grau</option>
        <option value="outline">Umriss</option>
        <option value="dotted" disabled={!dotted}>
          Gepunktet
        </option>
      </select>
      {!dotted && <p className="hint">Gepunktet gibt es nur in der Grundschrift (Urff).</p>}
      {trace !== "off" && (
        <button className={fade ? "on" : ""} aria-pressed={!!fade} onClick={() => onChange({ fade: fade ? undefined : "row" })}>
          Ausblenden
        </button>
      )}
      {fade && (
        <div className="seg">
          <button className={fade === "row" ? "on" : ""} aria-pressed={fade === "row"} onClick={() => onChange({ fade: "row" })}>
            In der Zeile
          </button>
          <button className={fade === "rows" ? "on" : ""} aria-pressed={fade === "rows"} onClick={() => onChange({ fade: "rows" })}>
            Von Zeile zu Zeile
          </button>
        </div>
      )}
    </>
  );
}
