// The format panel's settings for a Zahlenstrahl block: its numbers, its ticks and its tasks.
import { useState } from "react";
import type { ZahlenstrahlBlock } from "../sheet";
import { draw } from "../bank";
import { count, crowded, made, MAX, sane, type Task, type ZahlenstrahlProps } from "../zahlenstrahl";

const LABELS = { all: "Bei jedem Strich", major: "Bei langen Strichen", ends: "Anfang und Ende", none: "Keine" } as const;

// A whole number in a field. The field keeps its draft while the number is one `sane` would not take.
function Whole({
  label,
  name,
  value,
  ok,
  apply,
}: {
  label: string;
  name: keyof ZahlenstrahlProps;
  value: number;
  ok: (v: number) => boolean;
  apply: (props: Partial<ZahlenstrahlProps>, key?: string) => void;
}) {
  const [draft, setDraft] = useState<string | null>(null);
  return (
    <label>
      {label}
      <input
        type="number"
        inputMode="numeric"
        aria-label={label}
        value={draft ?? String(value)}
        onChange={(e) => {
          const text = e.target.value;
          setDraft(text);
          if (/^\d+$/.test(text) && ok(Number(text))) apply({ [name]: Number(text) }, name);
        }}
        onBlur={() => setDraft(null)}
      />
    </label>
  );
}

export default function Zahlenstrahl({ block, apply }: { block: ZahlenstrahlBlock; apply: (props: Partial<ZahlenstrahlProps>, key?: string) => void }) {
  const p = sane(block.props);
  const m = made(p);
  // Whether `sane` takes the number as it is, so the stored value is the typed one.
  const takes = (name: keyof ZahlenstrahlProps) => (v: number) => sane({ ...p, [name]: v, ...(name === "start" && { end: MAX }) })[name] === v;
  // A start at or past the end takes the end along to start + 20, as `sane` does: 340 typed into 0 to 20 gives 340 to 360.
  // A small step the long step is no multiple of stores the long step the line then draws, so the field shows what is stored.
  const moveMinor = (props: Partial<ZahlenstrahlProps>, key?: string) => {
    const minor = props.minor!;
    apply(p.major % minor === 0 ? { minor } : { minor, major: sane({ ...p, minor }).major }, key);
  };
  const moveStart =(props: Partial<ZahlenstrahlProps>, key?: string) => {
    const start = props.start!;
    apply(start < p.end ? { start } : { start, end: Math.min(start + 20, MAX) }, key);
  };
  const marks = p.marks ?? [];
  const cycle = (value: number) => {
    const task: Task | undefined = marks.find((mk) => mk[0] === value)?.[1];
    const next: Task | undefined = task === undefined ? "box" : task === "box" ? "arrow" : undefined;
    const rest = marks.filter((mk) => mk[0] !== value);
    apply({ marks: next ? [...rest, [value, next]] : rest });
  };

  return (
    <>
      <h2>Zahlenstrahl</h2>
      <Whole label="Anfang" name="start" value={p.start} ok={takes("start")} apply={moveStart} />
      <Whole label="Ende" name="end" value={p.end} ok={takes("end")} apply={apply} />
      <Whole label="Schritt kleine Striche" name="minor" value={p.minor} ok={takes("minor")} apply={moveMinor} />
      <Whole label="Schritt lange Striche" name="major" value={p.major} ok={takes("major")} apply={apply} />
      <select aria-label="Zahlen" value={p.labels} onChange={(e) => apply({ labels: e.target.value as ZahlenstrahlProps["labels"] })}>
        {Object.entries(LABELS).map(([labels, text]) => (
          <option key={labels} value={labels}>
            {text}
          </option>
        ))}
      </select>
      <Whole label="Schriftgröße" name="size" value={p.size} ok={takes("size")} apply={apply} />
      <label>
        <input type="checkbox" aria-label="Bruchstelle" checked={p.cut} disabled={p.start === 0} onChange={() => apply({ cut: !p.cut })} />
        Bruchstelle
      </label>
      <select aria-label="Aufgaben" value={p.tasks} onChange={(e) => apply({ tasks: e.target.value as ZahlenstrahlProps["tasks"] })}>
        <option value="random">Zufällig</option>
        <option value="free">Selbst wählen</option>
      </select>
      {p.tasks === "random" && (
        <>
          <div className="seg">
            <button aria-label="Ein Kästchen weniger" disabled={p.boxes === 0} onClick={() => apply({ boxes: p.boxes - 1 })}>
              −
            </button>
            <output>{`${p.boxes} Kästchen`}</output>
            <button aria-label="Ein Kästchen mehr" disabled={p.boxes === 12} onClick={() => apply({ boxes: p.boxes + 1 })}>
              ＋
            </button>
          </div>
          <div className="seg">
            <button aria-label="Ein Pfeil weniger" disabled={p.arrows === 0} onClick={() => apply({ arrows: p.arrows - 1 })}>
              −
            </button>
            <output>{`${p.arrows} Pfeile`}</output>
            <button aria-label="Ein Pfeil mehr" disabled={p.arrows === 6} onClick={() => apply({ arrows: p.arrows + 1 })}>
              ＋
            </button>
          </div>
          <button className="wide" onClick={() => apply({ seed: draw([{ seed: p.seed, show: (seed) => JSON.stringify(made({ ...p, seed }).ticks.map((t) => t.task)) }]) })}>
            Neu würfeln
          </button>
        </>
      )}
      {p.tasks === "free" &&
        (count(p) > 200 ? (
          <p className="hint" data-hint="many">Mehr als 200 Striche: Größeren Schritt wählen, dann lassen sich die Aufgaben setzen.</p>
        ) : (
          <div className="strahl">
            {m.ticks.map((t) => (
              <button
                key={t.value}
                aria-label={`Strich ${t.value}`}
                data-task={t.task}
                aria-pressed={t.task ? true : undefined}
                onClick={() => cycle(t.value)}
              >
                {t.value}
              </button>
            ))}
          </div>
        ))}
      {crowded(p, block.w) && (
        <p className="hint warn" role="status">
          Die Striche stehen enger als 1 mm. Größerer Schritt oder breiterer Block.
        </p>
      )}
      <label>
        <input type="checkbox" aria-label="Sprungbögen" checked={p.jumps} onChange={() => apply({ jumps: !p.jumps })} />
        Sprungbögen
      </label>
      {p.jumps && (
        <>
          <Whole label="Sprungweite" name="jump" value={p.jump ?? p.major} ok={takes("jump")} apply={apply} />
          {m.arcs.map((arc, i) => (
            <input
              key={arc.from}
              type="text"
              aria-label={`Bogen ${i + 1}`}
              placeholder={`+${p.jump ?? p.major}`}
              value={p.arcs?.[i] ?? ""}
              onChange={(e) => {
                // As long as the stored labels at least: those of arcs a shorter line hides now come back with it.
                const arcs = Array.from({ length: Math.max(p.arcs?.length ?? 0, i + 1) },(_, j) => (j === i ? e.target.value || null : (p.arcs?.[j] ?? null)));
                apply({ arcs }, `arc:${i}`);
              }}
            />
          ))}
        </>
      )}
    </>
  );
}
