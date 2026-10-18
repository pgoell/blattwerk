// The format panel's settings for a maths block: every limit of the generator in one place.
import { useEffect, useLayoutEffect, useRef, useState, useSyncExternalStore } from "react";
import { flushSync } from "react-dom";
import { post, signed } from "../api";
import Numbering from "../components/Numbering";
import { attempt, drop } from "../fault";
// A type alone: the module itself needs a window, and the sheet model's tests load this one without.
import type { Owed } from "../saves";
import { decimalsOf, overFoot, scaleOf, SIGNS, subscribe, type Limits, type Made, type MathsBlock, type MathsProps, type Op, type Range } from "../sheet";

const ROOMS = [10, 20, 100, 1000, 1000000];
// Einer, Zehner, Hunderter, Tausender and so on up to the million.
const PLACES = ["E", "Z", "H", "T", "ZT", "HT", "M"];
// The places after the comma, Zehntel first, with their labels in the rows and their names for the pupil's ear.
const FRACTIONS = [["z", "Zehntel"], ["h", "Hundertstel"]] as const;
// A number's digit ranges: its whole places by its name, or the places after the comma by AFTER.
type Key = "a" | "b" | "c" | "af" | "bf" | "cf";
const AFTER = { a: "af", b: "bf", c: "cf" } as const;
const NACH = ["0 Nachkommastellen", "1 Nachkommastelle", "2 Nachkommastellen"];
const DIGITS = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9];
const CARRIES = [["none", "Ohne"], ["required", "Mit"], ["either", "Egal"]] as const;
const FORMATS = [["row", "Zeile"], ["gap", "Lücke"], ["written", "Schriftlich"], ["compare", "Vergleichen"]] as const;
const SIDES = [["nn", "Zahl ○ Zahl"], ["tn", "Aufgabe ○ Zahl"], ["tt", "Aufgabe ○ Aufgabe"]] as const;
const LOOSEN: Record<string, string> = { carry: "Übertrag", rest: "Rest", a: "Ziffern der 1. Zahl", b: "Ziffern der 2. Zahl", c: "Ziffern der 3. Zahl", max: "Zahlenraum", close: "Knapp", equal: "Aufgaben mit =", brackets: "Klammern", family: "Aufgabenfamilien", zero: "Aufgaben mit 0", one: "Aufgaben mit 1 beim Malnehmen und Teilen", distinct: "keine gleichen Zahlen", small: "Kleines Einmaleins" };
const GAPS = ["a", "b", "c", "result"] as const;
const FAMILIES = [["none", "Keine"], ["swap", "Tauschaufgaben"], ["reverse", "Umkehraufgaben"], ["neighbour", "Nachbaraufgaben"]] as const;
const NTH = { a: "1. Zahl", b: "2. Zahl", c: "3. Zahl" } as const;

export const newSeed = () => Math.floor(Math.random() * 1e9);
// The limits the server reads from a request, and nothing else.
const ask = ({ ops, max, a, b, c, carry, rest, format, count, seed, sides, close, equal, numbers, pvs, brackets, decimals, money, af, bf, cf, family, moves, gaps, zero, one, distinct, small }: Limits) => ({ ops, max, a, b, c, carry, rest, format, count, seed, sides, close, equal, numbers, pvs, brackets, decimals, money, af, bf, cf, family, moves, gaps, zero, one, distinct, small });
// Asked with the session run out, it brings the login.
export const generate = (l: Limits) => signed(post<Made>("/maths", ask(l)));
// Any digit in each place of a Zahlenraum.
const anyDigits = (max: number): Range[] => Array.from(String(max), (): Range => [0, 9]);

export default function Maths({ block, apply, foot, owe }: { block: MathsBlock; apply: (props: MathsProps, key?: string) => boolean; foot: number; owe: (entry: Owed) => void }) {
  // The changed limits of the clicks still on their way, shown until the server's exercises for them are on the sheet.
  const [pending, setPending] = useState<Partial<Limits>>();
  const [own, setOwn] = useState(!ROOMS.includes(block.props.max));
  // What is typed in the own Zahlenraum, until an undo or a redo changes the number under the field.
  const [typed, setTyped] = useState<string>();
  useEffect(() => setTyped(undefined), [block.props.max]);
  // Why a typed number is not the Zahlenraum: the exercises keep the one they have.
  const wrong = !typed ? "" : +typed > 1000000 ? "Höchstens 1.000.000." : +typed < 1 ? "Mindestens 1." : !Number.isInteger(+typed) ? "Nur ganze Zahlen." : "";
  // The props of the last change the page had no room for. The line shows while they would still grow the block past the foot.
  const [denied, setDenied] = useState<MathsProps>();
  const refused = !!denied && overFoot(block, denied, foot);
  const line = useRef<HTMLParagraphElement>(null);
  useEffect(() => {
    if (refused) line.current?.scrollIntoView({ block: "nearest" });
  }, [refused]);
  const asked = useRef(0);
  // The answers are applied in the order of the clicks: each waits for the one before it.
  const applying = useRef<Promise<unknown>>(Promise.resolve());
  // The click whose answer is on the sheet: a retried older one comes too late to count.
  const landed = useRef(0);
  // The block's own limits as it has them now, and the changes of clicks that failed: the next click carries them.
  const stored = useRef(block.props);
  const carry = useRef<Partial<Limits>>({});
  const p = pending ? ({ ...block.props, ...pending } as MathsProps) : block.props;
  // The scale the block draws at: its tasks may be too wide for its columns.
  const scale = useSyncExternalStore(subscribe, () => scaleOf(block.id));
  const tried = (props: MathsProps, key?: string) => {
    const ok = apply(props, key);
    setDenied(ok ? undefined : props);
    return ok;
  };
  // The `tried` of the last render: an answer that waited for the one before it is measured on the block that one left.
  const latest = useRef(tried);
  useLayoutEffect(() => {
    latest.current = tried;
    stored.current = block.props;
  });

  // A new limit asks for new exercises. Every answer is applied, in the order asked; only the last one clears the
  // pending limit. Where none comes, the limit stays as set, and the line above the page asks again with it.
  // The changes of the clicks still on their way, by click. A refused one leaves the panel with its answer.
  const onWay = useRef(new Map<number, Partial<Limits>>());
  // What the panel shows over the block: the failed clicks' changes, then those on their way, in click order.
  function wish() {
    const all = Object.assign({ ...carry.current }, ...onWay.current.values()) as Partial<Limits>;
    setPending(Object.keys(all).length ? all : undefined);
    return all;
  }
  function limit(change: Partial<Limits>) {
    const n = ++asked.current;
    onWay.current.set(n, change);
    const sent = { ...stored.current, ...wish() };
    const before = applying.current;
    applying.current = attempt("Die Aufgaben konnten nicht erzeugt werden.", async () => {
      // The session ran out: the saver keeps the change, so the red bar shows and the editor redoes it after the login.
      const owed = (e: unknown) => {
        if ((e as Error).message === "401") owe({ block: block.id, change });
      };
      // A failed click keeps its change for the next click to carry.
      const miss = (e: unknown) => {
        carry.current = { ...carry.current, ...change };
        onWay.current.delete(n);
        wish();
        return e;
      };
      let made: Made | undefined;
      let error: unknown;
      try {
        made = await generate(sent);
      } catch (e) {
        owed(e);
        error = e;
      }
      await before;
      // A click a later one has overtaken says nothing, not even when its request failed.
      if (n < landed.current) {
        onWay.current.delete(n);
        wish();
        return;
      }
      if (error) throw miss(error);
      const base = () => ({ ...stored.current, ...carry.current, ...change });
      // An earlier click refused in between is no limit of this one: the answer is asked again without it.
      if (JSON.stringify(ask(base())) !== JSON.stringify(ask(sent)))
        made = await generate(base()).catch((e) => {
          owed(e);
          return Promise.reject(miss(e));
        });
      landed.current = n;
      // Drawn at once, so that the next answer's `latest` sees the block as this one leaves it. Each answer is an
      // undo step of its own, also when two land after both clicks. Built after the answer, so that a column
      // clicked while it was on its way stays.
      let ok = false;
      flushSync(() => void (ok = latest.current({ ...base(), ...made }, `maths ${n}`)));
      // The line of an earlier failed click is moot now: its change is on the sheet with this answer.
      if (ok) {
        carry.current = {};
        drop("Die Aufgaben konnten nicht erzeugt werden.");
      }
      onWay.current.delete(n);
      wish();
      if (n !== asked.current) return;
      // A refused own Zahlenraum drops its number from the field: the block's own number shows, as on leaving it.
      if (!ok && change.max) setTyped((t) => (t === String(change.max) ? undefined : t));
    });
  }
  // The typed number applies on Enter and on leaving the field, when it is a Zahlenraum; the field then shows the number in use.
  function commit() {
    if (typed && !wrong) room(Math.floor(+typed));
    setTyped(undefined);
  }
  // A number has as many places as the Zahlenraum; a new place takes any digit.
  function room(max: number) {
    const fit = (places: Range[]) => Array.from(String(max), (_, i) => places[i] ?? [0, 9]);
    // A block that never had a third number gets none here: the same Zahlenraum again changes nothing.
    limit({ max, a: fit(p.a), b: fit(p.b), ...(p.c && { c: fit(p.c) }) });
  }
  function toggle(op: Op) {
    const ops = p.ops.includes(op) ? p.ops.filter((o) => o !== op) : [...p.ops, op];
    if (ops.length) limit({ ops });
  }
  // The places after the comma are af, bf and cf, two entries always; a missing one is any digit.
  function ranges(key: Key): Range[] {
    return key.length > 1 ? [0, 1].map((i) => p[key]?.[i] ?? [0, 9]) : p[key] ?? anyDigits(p.max);
  }
  // The lowest digit of a place never lies above its highest: the other end moves along.
  function digit(key: Key, place: number, end: 0 | 1, to: number) {
    const range = ([lo, hi]: Range): Range => (end ? [Math.min(lo, to), to] : [to, Math.max(hi, to)]);
    limit({ [key]: ranges(key).map((r, i) => (i === place ? range(r) : r)) });
  }
  const show = (change: Partial<MathsProps>) => tried({ ...block.props, ...change });
  const plus = p.ops.includes("+") || p.ops.includes("-");
  const times = p.ops.includes("*") || p.ops.includes("/");
  // Times, divide and compare keep whole numbers: the places after the comma stay greyed then, and keep their value.
  const open = !times && p.format !== "compare";
  const dec = decimalsOf(p);
  const money = open && !!p.money;
  // Three numbers come in rows and gaps only. Punkt vor Strich needs three numbers and a sign of each kind; the
  // switches stay on the panel, greyed, when they do not hold. Brackets need Punkt vor Strich.
  const numbered = p.format === "row" || p.format === "gap";
  const three = numbered && p.numbers === 3;
  const free = three && plus && times;
  const pvs = free && !!p.pvs;
  const brackets = pvs && !!p.brackets;
  // Families hold for Zeile and Lücke with two numbers. Tauschaufgaben need a plus or a times, the only signs they draw.
  const swap = p.ops.includes("+") || p.ops.includes("*");
  const fam = numbered && !three && !!p.family && p.family !== "none" && !(p.family === "swap" && !swap);
  const families = new Set(p.exercises.map((e) => ("family" in e ? e.family : undefined))).size;
  const whole = fam && p.family === "reverse";
  // The Lücke boxes: the block's gaps, a block saved before has none, which is every number. A hidden c keeps its tick.
  const all = p.gaps ?? ["a", "b", "c"];
  const shown = GAPS.filter((k) => k !== "c" || three);
  const ticked = shown.filter((k) => all.includes(k));
  const lit = ticked.length ? ticked : shown.filter((k) => k !== "result");
  // The last ticked box stays ticked, as the last sign of Rechenart does.
  function gap(k: (typeof GAPS)[number]) {
    const next = GAPS.filter((g) => (g === k ? !lit.includes(g) : shown.includes(g) ? lit.includes(g) : all.includes(g)));
    if (shown.some((g) => next.includes(g))) limit({ gaps: next });
  }

  return (
    <>
      <h2>Rechenart</h2>
      <div className="seg">
        {(Object.keys(SIGNS) as Op[]).map((op) => (
          <button key={op} className={p.ops.includes(op) ? "on" : ""} aria-pressed={p.ops.includes(op)} onClick={() => toggle(op)}>
            {SIGNS[op]}
          </button>
        ))}
      </div>
      <div className="seg switch">
        <button className={p.zero !== false ? "on" : ""} aria-pressed={p.zero !== false} onClick={() => limit({ zero: p.zero === false })}>
          Aufgaben mit 0
        </button>
      </div>
      <div className="seg switch">
        <button className={p.one !== false ? "on" : ""} aria-pressed={p.one !== false} disabled={!times} onClick={() => limit({ one: p.one === false })}>
          Aufgaben mit 1 beim Malnehmen und Teilen
        </button>
      </div>
      <div className="seg switch">
        <button className={p.small ? "on" : ""} aria-pressed={!!p.small} disabled={!times || three} onClick={() => limit({ small: !p.small })}>
          Kleines Einmaleins
        </button>
      </div>
      <div className="seg switch">
        <button className={p.distinct ? "on" : ""} aria-pressed={!!p.distinct} onClick={() => limit({ distinct: !p.distinct })}>
          keine gleichen Zahlen
        </button>
      </div>
      <h2>Zahlenraum</h2>
      <select
        aria-label="Zahlenraum"
        value={own ? "" : p.max}
        onChange={(e) => {
          setOwn(!e.target.value);
          if (e.target.value) room(+e.target.value);
        }}
      >
        {ROOMS.map((max) => (
          <option key={max} value={max}>
            bis {max.toLocaleString("de")}
          </option>
        ))}
        <option value="">Eigener</option>
      </select>
      {own && (
        <input
          type="number"
          aria-label="Größte Zahl"
          min={1}
          max={1000000}
          value={typed ?? p.max}
          onChange={(e) => setTyped(e.target.value)}
          // Enter and leaving the field apply what is typed, when it fits, and show the number in use.
          onKeyDown={(e) => e.key === "Enter" && commit()}
          onBlur={commit}
        />
      )}
      {own && wrong && <p className="hint" role="status">{wrong} Die Aufgaben gehen bis {p.max.toLocaleString("de")}.</p>}
      <h2>Nachkommastellen</h2>
      <div className="seg">
        {([0, 1, 2] as const).map((n) => (
          // With Geld on, a number takes its place in one step: Geld goes off and the number is lit.
          <button key={n} aria-label={NACH[n]} className={dec === n && !money ? "on" : ""} aria-pressed={dec === n && !money} disabled={!open} onClick={() => limit({ decimals: n, money: false })}>
            {n}
          </button>
        ))}
        <button className={money ? "on" : ""} aria-pressed={money} disabled={!open} onClick={() => limit({ money: !p.money })}>
          Geld
        </button>
      </div>
      {(["a", "b", "c"] as const).slice(0, three ? 3 : 2).map((who) => {
        // One row of a place: its label, then the lowest and the highest digit.
        const row = (key: Key, i: number, label: string, name: string) => [
          <span key={i}>{label}</span>,
          ...([0, 1] as const).map((end) => (
            <select key={`${i}${end}`} aria-label={`${name} ${end ? "bis" : "von"}`} value={ranges(key)[i][end]} onChange={(e) => digit(key, i, end, +e.target.value)}>
              {DIGITS.map((d) => (
                <option key={d}>{d}</option>
              ))}
            </select>
          )),
        ];
        return (
          <div key={who}>
            <h2>{NTH[who]}: Ziffern von, bis</h2>
            <div className="places">
              {ranges(who).map((_, i) => row(who, i, PLACES[i], PLACES[i])).reverse()}
              {ranges(AFTER[who]).slice(0, dec).map((_, i) => row(AFTER[who], i, FRACTIONS[i][0], FRACTIONS[i][1]))}
            </div>
          </div>
        );
      })}
      {plus && (
        <>
          <h2>Übertrag</h2>
          <div className="seg">
            {CARRIES.map(([carry, label]) => (
              <button key={carry} className={p.carry === carry ? "on" : ""} onClick={() => limit({ carry })}>
                {label}
              </button>
            ))}
          </div>
        </>
      )}
      {p.ops.includes("/") && p.format !== "compare" && !three && (
        <>
          <h2>Division</h2>
          <div className="seg">
            {/* An Umkehraufgabe leaves no Rest: the buttons are greyed and show that, and keep their value. */}
            <button className={p.rest && !whole ? "" : "on"} disabled={whole} onClick={() => limit({ rest: false })}>Ohne Rest</button>
            <button className={p.rest && !whole ? "on" : ""} disabled={whole} onClick={() => limit({ rest: true })}>Mit Rest</button>
          </div>
        </>
      )}
      <h2>Format</h2>
      <div className="seg">
        {FORMATS.map(([format, label]) => (
          <button key={format} className={p.format === format ? "on" : ""} onClick={() => limit({ format })}>
            {label}
          </button>
        ))}
      </div>
      {p.format === "gap" && (
        <>
          <h2>Lücke</h2>
          <div className="seg">
            {shown.map((k) => (
              <button key={k} aria-label={`Lücke: ${k === "result" ? "Ergebnis" : NTH[k]}`} className={lit.includes(k) ? "on" : ""} aria-pressed={lit.includes(k)} onClick={() => gap(k)}>
                {k === "result" ? "Ergebnis" : NTH[k]}
              </button>
            ))}
          </div>
        </>
      )}
      {numbered && (
        <>
          <h2>Zahlen pro Aufgabe</h2>
          <div className="seg">
            <button aria-label="2 Zahlen" className={three ? "" : "on"} aria-pressed={!three} onClick={() => limit({ numbers: 2 })}>
              2
            </button>
            {/* A third number starts with any digit in each place, unless the block has digits for it already. */}
            <button aria-label="3 Zahlen" className={three ? "on" : ""} aria-pressed={three} onClick={() => limit({ numbers: 3, c: p.c ?? anyDigits(p.max) })}>
              3
            </button>
          </div>
          <div className="seg">
            <button className={pvs ? "on" : ""} aria-pressed={pvs} disabled={!free} onClick={() => limit({ pvs: !p.pvs })}>
              Punkt vor Strich
            </button>
            <button className={brackets ? "on" : ""} aria-pressed={brackets} disabled={!pvs} onClick={() => limit({ brackets: !p.brackets })}>
              mit Klammern
            </button>
          </div>
          <h2>Aufgabenfamilien</h2>
          <select aria-label="Aufgabenfamilien" value={p.family ?? "none"} disabled={three} onChange={(e) => limit({ family: e.target.value as Limits["family"] })}>
            {FAMILIES.map(([family, label]) => (
              <option key={family} value={family}>
                {label}
              </option>
            ))}
          </select>
          {p.family === "neighbour" && !three && (
            <div className="seg">
              <button aria-label="1. Zahl wandert" className={(p.moves ?? "a") === "a" ? "on" : ""} aria-pressed={(p.moves ?? "a") === "a"} onClick={() => limit({ moves: "a" })}>
                1. Zahl
              </button>
              <button aria-label="2. Zahl wandert" className={p.moves === "b" ? "on" : ""} aria-pressed={p.moves === "b"} onClick={() => limit({ moves: "b" })}>
                2. Zahl
              </button>
            </div>
          )}
          {numbered && !three && p.family === "swap" && (p.ops.includes("-") || p.ops.includes("/")) && <p className="hint" role="status">Tauschaufgaben gibt es nur für + und ·.</p>}
        </>
      )}
      {p.format === "compare" && (
        <>
          <h2>Seiten</h2>
          <select aria-label="Seiten" value={p.sides ?? "tn"} onChange={(e) => limit({ sides: e.target.value as Limits["sides"] })}>
            {SIDES.map(([sides, label]) => (
              <option key={sides} value={sides}>
                {label}
              </option>
            ))}
          </select>
          <h2>Abstand</h2>
          <div className="seg">
            <button className={p.close ? "" : "on"} aria-pressed={!p.close} onClick={() => limit({ close: false })}>Beliebig</button>
            <button className={p.close ? "on" : ""} aria-pressed={!!p.close} onClick={() => limit({ close: true })}>Knapp</button>
          </div>
          <h2>Aufgaben mit =</h2>
          <div className="seg">
            <button className={p.equal === "none" ? "on" : ""} aria-label="Keine mit =" aria-pressed={p.equal === "none"} onClick={() => limit({ equal: "none" })}>Keine</button>
            <button className={p.equal === "none" ? "" : "on"} aria-label="Einige mit =" aria-pressed={p.equal !== "none"} onClick={() => limit({ equal: "some" })}>Einige</button>
          </div>
        </>
      )}
      <h2>Anzahl</h2>
      <div className="seg">
        <button aria-label="Eine Aufgabe weniger" onClick={() => limit({ count: Math.max(1, p.count - 1) })}>−</button>
        <output>{p.count === 1 ? (fam ? "1 Familie" : "1 Aufgabe") : fam ? `${p.count} Familien` : `${p.count} Aufgaben`}</output>
        <button aria-label="Eine Aufgabe mehr" onClick={() => limit({ count: Math.min(100, p.count + 1) })}>＋</button>
      </div>
      {fam && <p className="hint">{p.exercises.length === 1 ? "Das ist 1 Aufgabe." : `Das sind ${p.exercises.length} Aufgaben.`}</p>}
      {refused && (
        <p className="hint" role="status" data-foot="full" ref={line}>
          Das passt nicht mehr auf die Seite: Der Block würde unten über den Rand ragen. Mehr Platz gibt es mit weniger Aufgaben, mehr Spalten, kleinerer Schrift oder weiter oben auf der Seite.
        </p>
      )}
      <div className="seg">
        <button aria-label="Eine Spalte weniger" onClick={() => show({ columns: Math.max(1, p.columns - 1) })}>−</button>
        <output>{p.columns === 1 ? "1 Spalte" : `${p.columns} Spalten`}</output>
        <button aria-label="Eine Spalte mehr" onClick={() => show({ columns: Math.min(6, p.columns + 1) })}>＋</button>
      </div>
      {scale < 0.97 && (
        <p className="hint" role="status">
          {p.columns > 1 ? `Für ${p.columns} Spalten sind die Aufgaben zu breit und stehen kleiner da. Mit weniger Spalten werden sie größer.` : "Die Aufgaben sind zu breit für den Block und stehen kleiner da."}
        </p>
      )}
      {p.format !== "written" && (
        <div className="seg">
          <button aria-label="Schrift kleiner" onClick={() => show({ size: Math.max(8, p.size - 2) })}>−</button>
          <output>{p.size} pt</output>
          <button aria-label="Schrift größer" onClick={() => show({ size: p.size + 2 })}>＋</button>
        </div>
      )}
      {p.loosen && (
        <p className="hint" role="status">
          {fam
            ? p.exercises.length
              ? `Mit diesen Grenzen gibt es nur ${families === 1 ? "1 Familie" : `${families} verschiedene Familien`}.`
              : "Mit diesen Grenzen gibt es keine Familie."
            : p.exercises.length
              ? `Mit diesen Grenzen gibt es nur ${p.exercises.length === 1 ? "1 Aufgabe" : `${p.exercises.length} verschiedene Aufgaben`}.`
              : "Mit diesen Grenzen gibt es keine Aufgabe."}
          {p.loosen.length > 0 && ` Mehr gibt es mit einer lockereren Grenze: ${p.loosen.map((name) => LOOSEN[name]).join(", ")}.`}
        </p>
      )}
      <button className="wide" onClick={() => limit({ seed: newSeed() })}>Neu würfeln</button>
      <h2>Aufgaben nummerieren</h2>
      <Numbering value={p.numbering} onChange={(numbering) => show({ numbering })} />
    </>
  );
}
