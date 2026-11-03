// The counts and switches of the Formen from #835. Each one shows only for the kind it belongs to.

import { bulgeOf, cornersOf, filledOf, partsOf, spikesOf } from "../../sheet/formen";
import type { TextProps } from "../../sheet";

const line = (kind?: string) => kind === "line" || kind === "arrow" || kind === "double";

type Boxed = { props: Partial<TextProps> & { kind?: TextProps["kind"] } };

function Step({ label, min, max, value, onChange }: { label: string; min: number; max: number; value: number; onChange: (n: number) => void }) {
  return (
    <label>
      {label}
      <input
        type="number"
        min={min}
        max={max}
        step={1}
        value={value}
        onChange={(e) => {
          const n = Math.round(+e.target.value);
          if (Number.isInteger(n) && n >= min && n <= max) onChange(n);
        }}
      />
    </label>
  );
}

export function FormenFields({ boxes, look }: { boxes: Boxed[]; look: (props: object, key?: string) => void }) {
  if (!boxes.length) return null;
  const props = boxes[0].props;
  const kind = props.kind;
  const same = boxes.every((b) => b.props.kind === kind);
  const form = boxes.every((b) => b.props.form === props.form) ? props.form : undefined;
  return (
    <>
      {same && kind === "polygon" && <Step label="Ecken" min={5} max={15} value={cornersOf(props)} onChange={(n) => look({ corners: n }, "corners")} />}
      {same && kind === "star" && <Step label="Zacken" min={3} max={35} value={spikesOf(props)} onChange={(n) => look({ spikes: n }, "spikes")} />}
      {same && (kind === "pie" || kind === "bars") && (
        <>
          <Step label="Teile" min={2} max={50} value={partsOf(props)} onChange={(n) => look({ parts: n, filled: Math.min(filledOf(props), n) }, "parts")} />
          <Step label="Gefüllt" min={0} max={partsOf(props)} value={filledOf(props)} onChange={(n) => look({ filled: n }, "filled")} />
        </>
      )}
      {same && kind === "circle" && (
        <label className="tick">
          <input type="checkbox" checked={props.hub === true} onChange={(e) => look({ hub: e.target.checked || undefined }, "hub")} /> Mittelpunkt
        </label>
      )}
      {same && (kind === "arc" || kind === "bow") && (
        <label>
          Wölbung
          <input type="range" min={-1} max={1} step={0.05} value={bulgeOf(props)} onChange={(e) => look({ bulge: Math.round(+e.target.value * 100) / 100 }, "bulge")} />
        </label>
      )}
      {boxes.every((b) => !line(b.props.kind)) && (
        <div className="seg">
          <button type="button" className={form === "square" ? "on" : ""} aria-pressed={form === "square"} onClick={() => look({ form: form === "square" ? undefined : "square" }, "form")}>
            Quadratisch
          </button>
          <button type="button" className={form === "round" ? "on" : ""} aria-pressed={form === "round"} onClick={() => look({ form: form === "round" ? undefined : "round" }, "form")}>
            Kreisförmig
          </button>
        </div>
      )}
    </>
  );
}
