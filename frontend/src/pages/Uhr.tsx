// The format panel's settings for an Uhr block: its face, its task, how a time is written, and the times.
import { useState } from "react";
import type { UhrBlock } from "../sheet";
import { parsed, sane, timesOf, type UhrProps } from "../uhr";
import { newSeed } from "./Maths";

type Apply = (props: Partial<UhrProps>, key?: string) => void;

const pad = (n: number) => String(n).padStart(2, "0");
const clock = (t: number) => `${Math.floor(t / 60)}:${pad(t % 60)}`;
const inRange = (lo: number, hi: number) => (v: number) => v >= lo && v <= hi;

// A whole number in a field. The field keeps its draft while the number is one `ok` would not take.
function Whole({
  label,
  name,
  value,
  ok,
  apply,
}: {
  label: string;
  name: keyof UhrProps;
  value: number;
  ok: (v: number) => boolean;
  apply: Apply;
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

// One clock's time as `h:mm`. A draft that does not parse is not stored and the field shows it as invalid.
function Time({ label, value, setTime }: { label: string; value: number; setTime: (t: number) => void }) {
  const [draft, setDraft] = useState<string | null>(null);
  return (
    <label>
      {label}
      <input
        type="text"
        aria-label={label}
        aria-invalid={draft !== null && parsed(draft) === undefined ? "true" : undefined}
        value={draft ?? clock(value)}
        onChange={(e) => {
          const text = e.target.value;
          setDraft(text);
          const t = parsed(text);
          if (t !== undefined) setTime(t);
        }}
        onBlur={() => setDraft(null)}
      />
    </label>
  );
}

export default function Uhr({ block, apply }: { block: UhrBlock; apply: Apply }) {
  const p = sane(block.props);
  const times = timesOf(p);

  return (
    <>
      <h2>Uhr</h2>
      <select aria-label="Zahlen" value={p.numbers} onChange={(e) => apply({ numbers: e.target.value as UhrProps["numbers"] })}>
        <option value="all">1 bis 12</option>
        <option value="quarters">12, 3, 6, 9</option>
        <option value="none">Keine</option>
      </select>
      <label>
        <input type="checkbox" aria-label="Minutenstriche" checked={p.minutes} onChange={() => apply({ minutes: !p.minutes })} />
        Minutenstriche
      </label>
      <label>
        <input type="checkbox" aria-label="13 bis 24" checked={p.ring} disabled={p.numbers === "none"} onChange={() => apply({ ring: !p.ring })} />
        13 bis 24
      </label>
      <select aria-label="Aufgabe" value={p.task} onChange={(e) => apply({ task: e.target.value as UhrProps["task"] })}>
        <option value="read">Uhrzeit ablesen</option>
        <option value="draw">Zeiger einzeichnen</option>
      </select>
      {p.task === "read" && (
        <select aria-label="Antwort" value={p.answer} onChange={(e) => apply({ answer: e.target.value as UhrProps["answer"] })}>
          <option value="box">__:__ Uhr</option>
          <option value="line">Linie</option>
        </select>
      )}
      <select aria-label="Schreibweise" value={p.format} onChange={(e) => apply({ format: e.target.value as UhrProps["format"] })}>
        <option value="12">3:30 Uhr</option>
        <option value="24">15:30 Uhr</option>
        <option value="words">In Worten</option>
      </select>
      {p.format === "words" && (
        <select aria-label="Form" value={p.region} onChange={(e) => apply({ region: e.target.value as UhrProps["region"] })}>
          <option value="nach">viertel nach drei</option>
          <option value="viertel">viertel vier</option>
        </select>
      )}
      <Whole label="Uhren" name="count" value={p.count} ok={inRange(1, 12)} apply={apply} />
      <Whole label="Spalten" name="cols" value={p.cols} ok={inRange(1, 6)} apply={apply} />
      <select
        aria-label="Zeiten"
        value={p.fill}
        onChange={(e) => {
          const fill = e.target.value as UhrProps["fill"];
          // Times typed before come back; the other clocks keep the times they show.
          apply(fill === "free" ? { fill, times: times.map((t, i) => ((p.times?.[i] ?? -1) >= 0 ? p.times![i] : t)) } : { fill });
        }}
      >
        <option value="random">Zufällig</option>
        <option value="free">Selbst wählen</option>
      </select>
      {p.fill === "random" && (
        <>
          <select aria-label="Schritte" value={p.step} onChange={(e) => apply({ step: Number(e.target.value) as UhrProps["step"] })}>
            <option value="60">Volle Stunden</option>
            <option value="30">Halbe Stunden</option>
            <option value="15">Viertelstunden</option>
            <option value="5">5 Minuten</option>
            <option value="1">1 Minute</option>
          </select>
          <button className="wide" onClick={() => apply({ seed: newSeed() })}>
            Neu würfeln
          </button>
        </>
      )}
      {p.fill === "free" &&
        times.map((t, i) => (
          <Time
            key={i}
            label={`Uhr ${i + 1}`}
            value={t}
            setTime={(v) => apply({ times: times.map((x, j) => (j === i ? v : x)) }, `time:${i}`)}
          />
        ))}
    </>
  );
}
