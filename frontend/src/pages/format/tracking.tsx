// The Zeichenabstand slider, and the warning that a cursive script's joins break.
import { trackingOf } from "../../sheet";

export function Tracking({ value, warn, onChange }: { value: unknown; warn: boolean; onChange: (n: number) => void }) {
  const n = trackingOf({ tracking: value });
  return (
    <>
      <label>
        Zeichenabstand
        <input type="range" min={0} max={1} step={0.05} value={n} onChange={(e) => onChange(Math.round(+e.target.value * 20) / 20)} />
      </label>
      {n > 0 && warn && (
        <p className="hint warn" role="status">
          Zeichenabstand trennt die Verbindungen dieser Schreibschrift.
        </p>
      )}
    </>
  );
}
