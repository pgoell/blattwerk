// The format panel's settings for a Rechentabelle block: its tables, rows and columns, Rechenart, Zahlenraum, Reihen, Farbe and the numbers typed in.
import { useRef, useState } from "react";
import type { RechentabelleBlock } from "../sheet";
import { draw } from "../bank";
import { FIRST, made, sane, type CarryRule, type Op, type RechentabelleProps, type RechentabelleTyped, type Tint } from "../rechentabelle";

type CarryTuple = [CarryRule, CarryRule];

const RECHENART = [
  ["+", "Plus"],
  ["-", "Minus"],
  ["*", "Mal"],
  [":", "Geteilt"],
] as const;
const ZAHLENRAUM = [10, 20, 100, 1000];
const TINTS: [Tint, string][] = [
  ["none", "Keine"],
  ["blue", "Blau"],
  ["green", "Grün"],
  ["yellow", "Gelb"],
  ["red", "Rot"],
  ["purple", "Lila"],
];

const plural = (n: number, one: string, many: string) => (n === 1 ? `1 ${one}` : `${n} ${many}`);

function stepper(less: string, more: string, text: string, n: number, lo: number, hi: number, down: () => void, up: () => void) {
  return (
    <div className="seg">
      <button aria-label={less} disabled={n <= lo} onClick={down}>
        −
      </button>
      <output>{text}</output>
      <button aria-label={more} disabled={n >= hi} onClick={up}>
        ＋
      </button>
    </div>
  );
}

export default function Rechentabelle({ block, apply }: { block: RechentabelleBlock; apply: (props: Partial<RechentabelleProps>, key?: string) => void }) {
  const p = sane(block.props);
  const m = made(p);
  const [which, setWhich] = useState(0);
  // The number field with focus keeps its own text, so that typing is not fought by the re-render.
  const [draft, setDraft] = useState<{ key: string; text: string } | null>(null);
  // Set when a number field gets focus, until the mouseup of that click has selected its number.
  const fresh = useRef(false);

  const c = Math.min(which, p.count - 1);
  const table = m.tables?.[c];
  const raw = Array.isArray(block.props.typed) ? block.props.typed : [];

  // The number the teacher typed for a box of table c, if any: as the sheet takes it (sane keeps the last valid one).
  const stored = (r: number, s: number) => p.typed?.find((e) => e[0] === c && e[1] === r && e[2] === s)?.[3];

  // The text a box shows: the typed number, else the table's number (a struck or made up cell shows nothing).
  function shownText(r: number, s: number): string {
    const typed = stored(r, s);
    if (typed !== undefined) return String(typed);
    if (!table) return "";
    if (r === 0) return String(table.cols[s - 1] ?? "");
    if (s === 0) return String(table.rows[r - 1] ?? "");
    if (table.struck[r - 1]?.[s - 1] || table.madeUp[r - 1]?.[s - 1]) return "";
    const v = table.cells[r - 1]?.[s - 1];
    return v === undefined ? "" : String(v);
  }

  function setTyped(r: number, s: number, text: string) {
    // The stored entries as they are, so that the other boxes and tables keep their numbers.
    const others = raw.filter((e) => Array.isArray(e) && (e[0] !== c || e[1] !== r || e[2] !== s));
    const key = `typed:${c}:${r}:${s}`;
    if (text === "") return apply({ typed: others.length ? others : undefined }, key);
    apply({ typed: [...others, [c, r, s, Number(text)] as RechentabelleTyped] }, key);
  }

  // A number field for the box of row r and column s (r 0 holds the column values, s 0 the row values).
  function numberField(r: number, s: number, label: string) {
    const key = `${c},${r},${s}`;
    const text = shownText(r, s);
    return (
      <input
        key={key}
        className="typed"
        inputMode="numeric"
        aria-label={label}
        value={draft?.key === key ? draft.text : text}
        onFocus={() => {
          fresh.current = true;
          setDraft({ key, text });
        }}
        // The click that focuses the field also places the caret; this mouseup selects the whole number instead.
        onMouseUp={(e) => {
          if (!fresh.current) return;
          fresh.current = false;
          e.preventDefault();
          e.currentTarget.select();
        }}
        onBlur={() => setDraft(null)}
        onKeyDown={(e) => {
          // Ctrl+Z and Ctrl+Y are the sheet's here: the field then shows the number that the undo or redo gives.
          if ((e.ctrlKey || e.metaKey) && /^[zy]$/i.test(e.key)) setDraft(null);
        }}
        onChange={(e) => {
          if (!/^\d{0,4}$/.test(e.target.value)) return;
          setDraft({ key, text: e.target.value });
          setTyped(r, s, e.target.value);
        }}
      />
    );
  }

  const mal = p.op === "*" || p.op === ":";

  // The Übertrag of one place: 0 Zehner, 1 Hunderter. A change applies the whole tuple.
  function carrySelect(place: number, label: string) {
    return (
      <label>
        {label}
        <select
          aria-label={label}
          value={p.carry[place]}
          onChange={(e) => {
            const next = [...p.carry] as CarryTuple;
            next[place] = e.target.value as CarryRule;
            apply({ carry: next });
          }}
        >
          <option value="either">Egal</option>
          <option value="required">Mit</option>
          <option value="none">Ohne</option>
        </select>
      </label>
    );
  }

  return (
    <>
      <h2>Rechentabelle</h2>
      {stepper("Eine Tabelle weniger", "Eine Tabelle mehr", plural(p.count, "Tabelle", "Tabellen"), p.count, 1, 4, () => apply({ count: p.count - 1 }), () => apply({ count: p.count + 1 }))}
      {stepper(
        "Weniger Tabellen nebeneinander",
        "Mehr Tabellen nebeneinander",
        `${p.columns} nebeneinander`,
        p.columns,
        1,
        3,
        () => apply({ columns: p.columns - 1 }),
        () => apply({ columns: p.columns + 1 }),
      )}
      {stepper(
        "Eine Zeile weniger",
        "Eine Zeile mehr",
        plural(p.rows, "Zeile", "Zeilen"),
        p.rows,
        2,
        10,
        // Fewer rows than hidden values: the hidden count falls in the same step.
        () => apply(p.hideRows > p.rows - 2 ? { rows: p.rows - 1, hideRows: p.rows - 2 } : { rows: p.rows - 1 }),
        () => apply({ rows: p.rows + 1 }),
      )}
      {stepper(
        "Eine Spalte weniger",
        "Eine Spalte mehr",
        plural(p.cols, "Spalte", "Spalten"),
        p.cols,
        2,
        10,
        () => apply(p.hideCols > p.cols - 2 ? { cols: p.cols - 1, hideCols: p.cols - 2 } : { cols: p.cols - 1 }),
        () => apply({ cols: p.cols + 1 }),
      )}
      {stepper(
        "Ein versteckter Zeilenwert weniger",
        "Ein versteckter Zeilenwert mehr",
        plural(p.hideRows, "Zeilenwert versteckt", "Zeilenwerte versteckt"),
        p.hideRows,
        0,
        p.rows - 1,
        () => apply({ hideRows: p.hideRows - 1 }),
        () => apply({ hideRows: p.hideRows + 1 }),
      )}
      {stepper(
        "Ein versteckter Spaltenwert weniger",
        "Ein versteckter Spaltenwert mehr",
        plural(p.hideCols, "Spaltenwert versteckt", "Spaltenwerte versteckt"),
        p.hideCols,
        0,
        p.cols - 1,
        () => apply({ hideCols: p.hideCols - 1 }),
        () => apply({ hideCols: p.hideCols + 1 }),
      )}
      <label>
        Rechenart
        <select aria-label="Rechenart" value={p.op} onChange={(e) => apply({ op: e.target.value as Op })}>
          {RECHENART.map(([op, label]) => (
            <option key={op} value={op}>
              {label}
            </option>
          ))}
        </select>
      </label>
      {mal ? (
        <>
          <div className="reihen">
            {Array.from({ length: 10 }, (_, i) => i + 1).map((n) => {
              const on = p.reihen.includes(n);
              return (
                <label key={n}>
                  <input
                    type="checkbox"
                    aria-label={`${n}er-Reihe`}
                    checked={on}
                    disabled={on && p.reihen.length === 1}
                    onChange={() => apply({ reihen: on ? p.reihen.filter((x) => x !== n) : [...p.reihen, n].sort((a, b) => a - b) })}
                  />
                  {n}
                </label>
              );
            })}
          </div>
          <label>
            Anordnung
            <select aria-label="Anordnung" value={p.order} onChange={(e) => apply({ order: e.target.value as RechentabelleProps["order"] })}>
              <option value="related">Verwandte Reihen nebeneinander</option>
              <option value="random">Zufällig</option>
            </select>
          </label>
          <label>
            Erstfaktor
            <select aria-label="Erstfaktor" value={p.first} onChange={(e) => apply({ first: e.target.value as RechentabelleProps["first"] })}>
              <option value="all">Alle (1 bis 10)</option>
              <option value="kings">Nur Königsaufgaben (1, 2, 5, 10)</option>
              <option value="near">Königsaufgaben ± 1 (3, 4, 6, 9)</option>
            </select>
          </label>
        </>
      ) : (
        <>
          <label>
            Zahlenraum
            <select aria-label="Zahlenraum" value={p.max} onChange={(e) => apply({ max: Number(e.target.value) })}>
              {ZAHLENRAUM.map((n) => (
                <option key={n} value={n}>
                  {`bis ${n}`}
                </option>
              ))}
            </select>
          </label>
          {carrySelect(0, "Zehnerübergang")}
          {p.max >= 1000 && carrySelect(1, "Hunderterübergang")}
        </>
      )}
      <label>
        Farbe
        <select aria-label="Farbe" value={p.tint} onChange={(e) => apply({ tint: e.target.value as Tint })}>
          {TINTS.map(([v, label]) => (
            <option key={v} value={v}>
              {label}
            </option>
          ))}
        </select>
      </label>
      <label>
        Eigene Zahlen
        <select aria-label="Rechentabelle für eigene Zahlen" value={c} onChange={(e) => setWhich(Number(e.target.value))}>
          {Array.from({ length: p.count }, (_, i) => (
            <option key={i} value={i}>
              {`Rechentabelle ${i + 1}`}
            </option>
          ))}
        </select>
      </label>
      <div className="mauer">
        <div className="mauer-row">
          <span />
          {Array.from({ length: p.cols }, (_, j) => numberField(0, j + 1, `Spaltenwert ${j + 1}`))}
        </div>
        {Array.from({ length: p.rows }, (_, i) => (
          <div className="mauer-row" key={i}>
            {numberField(i + 1, 0, `Zeilenwert ${i + 1}`)}
            {Array.from({ length: p.cols }, (_, j) => numberField(i + 1, j + 1, `Zeile ${i + 1}, Spalte ${j + 1}`))}
          </div>
        ))}
      </div>
      {m.tables?.map((t, i) =>
        t.wrong ? (
          <p key={i} className="hint" role="status">{`Rechentabelle ${i + 1}: Die Zahlen passen nicht zusammen.`}</p>
        ) : null,
      )}
      {m.loose === "carry" && (
        <p className="hint" role="status">
          Mit dieser Übertrag-Regel gibt es nicht genug verschiedene Zahlen: manche Werte kommen zweimal vor.
        </p>
      )}
      {m.loose === "distinct" && (
        <p className="hint" role="status">
          Der Zahlenraum ist zu klein: manche Werte kommen zweimal vor.
        </p>
      )}
      {mal && (p.cols > p.reihen.length || p.rows > FIRST[p.first].length) && (
        <p className="hint" role="status">
          Mehr Zeilen oder Spalten als Reihen oder Erstfaktoren: Werte wiederholen sich.
        </p>
      )}
      {p.typed && (
        <button
          onClick={() => {
            setDraft(null);
            apply({ typed: undefined });
          }}
        >
          Eigene Zahlen entfernen
        </button>
      )}
      <button className="wide" onClick={() => apply({ seed: draw([{ seed: p.seed, show: (seed) => JSON.stringify(made({ ...p, seed }).tables) }]) })}>
        Neu würfeln
      </button>
    </>
  );
}
