// The format panel for a Textaufgabe: theme, operation, Zahlenraum, which parts the pupil sees, and the teacher's own text.
import { useState } from "react";
import type { TextaufgabeBlock } from "../sheet";
import { newSeed } from "./Maths";
import { OPS, THEMES, made, sane, type TextOp, type TextaufgabeProps, type TextaufgabeWritten, type Theme } from "../textaufgabe";

const THEME: Record<Theme, string> = { kurz: "Kurze Texte", sach: "Sachaufgaben", raetsel: "Rätsel", zeit: "Zeit", geld: "Geld" };
const OP: Record<TextOp, string> = { "+": "+", "-": "−", "*": "·", ":": ":" };

type Apply = (props: Partial<TextaufgabeProps>, key?: string) => void;

function blank(tasks: ReturnType<typeof made>["tasks"]): TextaufgabeWritten[] {
  return tasks.map((t) => ({ text: t.text, frage: t.frage, rechnung: t.rechnung, antwort: t.antwort }));
}

export default function Textaufgabe({ block, apply }: { block: TextaufgabeBlock; apply: Apply }) {
  const p = sane(block.props);
  const tasks = made(p).tasks;
  const [which, setWhich] = useState(0);
  const at = Math.min(which, tasks.length - 1);
  const loose = tasks.some((t) => !t.fit);

  function toggleTheme(theme: Theme) {
    const themes = p.themes.includes(theme) ? p.themes.filter((t) => t !== theme) : [...p.themes, theme];
    if (themes.length) apply({ themes }, "themes");
  }

  function toggleOp(op: TextOp) {
    const ops = p.ops.includes(op) ? p.ops.filter((o) => o !== op) : [...p.ops, op];
    if (ops.length) apply({ ops }, "ops");
  }

  function own(on: boolean) {
    if (!on) return apply({ manual: false }, "manual");
    apply({ manual: true, written: blank(tasks) }, "manual");
  }

  function roll() {
    const seed = newSeed();
    if (!p.manual) return apply({ seed }, "seed");
    apply({ seed, written: blank(made({ ...p, seed }).tasks) }, "seed");
  }

  function write(part: keyof TextaufgabeWritten, value: string) {
    const rows = blank(tasks);
    const had = p.written ?? [];
    had.forEach((row, i) => {
      if (rows[i]) rows[i] = row;
    });
    rows[at] = { ...rows[at], [part]: value };
    apply({ manual: true, written: rows }, `written:${at}:${part}`);
  }

  const row = p.written?.[at];
  return (
    <>
      <h2>Textaufgaben</h2>
      <div className="seg">
        <button aria-label="Eine Aufgabe weniger" disabled={p.count === 1} onClick={() => apply({ count: p.count - 1 }, "count")}>−</button>
        <output>{p.count === 1 ? "1 Aufgabe" : `${p.count} Aufgaben`}</output>
        <button aria-label="Eine Aufgabe mehr" disabled={p.count === 4} onClick={() => apply({ count: p.count + 1 }, "count")}>＋</button>
      </div>
      {THEMES.map((theme) => (
        <label key={theme}>
          <input type="checkbox" aria-label={THEME[theme]} checked={p.themes.includes(theme)} onChange={() => toggleTheme(theme)} />
          {THEME[theme]}
        </label>
      ))}
      {p.themes.includes("zeit") && (
        <select aria-label="Zeit" value={p.zeit} onChange={(e) => apply({ zeit: e.target.value as TextaufgabeProps["zeit"] }, "zeit")}>
          <option value="both">Zeitpunkte und Dauern</option>
          <option value="punkt">Zeitpunkte</option>
          <option value="dauer">Dauern</option>
        </select>
      )}
      <div className="seg">
        {OPS.map((op) => (
          <button key={op} className={p.ops.includes(op) ? "on" : ""} aria-pressed={p.ops.includes(op)} aria-label={op === "+" ? "Plus" : op === "-" ? "Minus" : op === "*" ? "Mal" : "Geteilt"} onClick={() => toggleOp(op)}>{OP[op]}</button>
        ))}
      </div>
      <select aria-label="Komplexität" value={p.steps} onChange={(e) => apply({ steps: Number(e.target.value) as 1 | 2 }, "steps")}>
        <option value={1}>Ein Schritt</option>
        <option value={2}>Zwei Schritte</option>
      </select>
      <select aria-label="Zahlenraum" value={p.max} onChange={(e) => apply({ max: Number(e.target.value) }, "max")}>
        {[10, 20, 100, 1000].map((n) => <option key={n} value={n}>bis {n}</option>)}
      </select>
      <select aria-label="Zahlen" value={p.numbers} onChange={(e) => apply({ numbers: e.target.value as TextaufgabeProps["numbers"] }, "numbers")}>
        <option value="whole">Natürliche Zahlen</option>
        <option value="decimal">Kommazahlen</option>
      </select>
      <select aria-label="Übergang" value={p.carry} onChange={(e) => apply({ carry: e.target.value as TextaufgabeProps["carry"] }, "carry")}>
        <option value="any">Übergang egal</option>
        <option value="yes">mit Übergang</option>
        <option value="no">ohne Übergang</option>
      </select>
      <label><input type="checkbox" aria-label="Frage zeigen" checked={p.frage} onChange={() => apply({ frage: !p.frage }, "frage")} />Frage zeigen</label>
      <label><input type="checkbox" aria-label="Rechnung zeigen" checked={p.rechnung} onChange={() => apply({ rechnung: !p.rechnung }, "rechnung")} />Rechnung zeigen</label>
      <label><input type="checkbox" aria-label="Antwort zeigen" checked={p.antwort} onChange={() => apply({ antwort: !p.antwort }, "antwort")} />Antwort zeigen</label>
      <label><input type="checkbox" aria-label="Zeichenfeld" checked={p.sketch} onChange={() => apply({ sketch: !p.sketch }, "sketch")} />Zeichenfeld</label>
      <select aria-label="Rechenzeilen" value={String(p.rows)} onChange={(e) => apply({ rows: e.target.value === "auto" ? "auto" : Number(e.target.value) }, "rows")}>
        <option value="auto">Rechenzeilen automatisch</option>
        {Array.from({ length: 8 }, (_, n) => n + 1).map((n) => <option key={n} value={n}>{n === 1 ? "1 Rechenzeile" : `${n} Rechenzeilen`}</option>)}
      </select>
      <label><input type="checkbox" aria-label="Eigene Texte" checked={p.manual} onChange={() => own(!p.manual)} />Eigene Texte</label>
      {p.manual && tasks.length > 1 && (
        <select aria-label="Aufgabe für eigene Texte" value={at} onChange={(e) => setWhich(Number(e.target.value))}>
          {tasks.map((_, i) => <option key={i} value={i}>Aufgabe {i + 1}</option>)}
        </select>
      )}
      {p.manual && (
        <>
          {(["text", "frage", "rechnung", "antwort"] as const).map((part) => (
            <label key={part}>
              {part === "text" ? "Text" : part === "frage" ? "Frage" : part === "rechnung" ? "Rechnung" : "Antwort"}
              <textarea aria-label={part === "text" ? "Text" : part === "frage" ? "Frage" : part === "rechnung" ? "Rechnung" : "Antwort"} rows={part === "rechnung" || part === "text" ? 3 : 2} value={row?.[part] ?? tasks[at][part]} onChange={(e) => write(part, e.target.value)} />
            </label>
          ))}
        </>
      )}
      {loose && <p className="hint" role="status">Mit diesen Einstellungen lässt sich der Übergang nicht bei jeder Aufgabe einhalten.</p>}
      <button className="wide" onClick={roll}>Neu würfeln</button>
    </>
  );
}
