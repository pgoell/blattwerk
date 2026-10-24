// Clicks still on their way: each answer lands in the order it was asked, and a failed one rides on the next.
import { useEffect, useLayoutEffect, useRef, useState, useSyncExternalStore } from "react";
import { flushSync } from "react-dom";
import { attempt, drop } from "../../fault";
import type { Owed } from "../../saves";
import { decimalsOf, overFoot, scaleOf, subscribe, type Limits, type Made, type MathsBlock, type MathsProps, type Op, type Range } from "../../sheet";
import { anyDigits, ask, GAPS, generate, kept, ROOMS, type Key } from "./ask";

export function useFlight(block: MathsBlock, apply: (props: MathsProps, key?: string) => boolean, foot: number, owe: (entry: Owed) => void) {
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
        error = e;
      }
      await before;
      // A click a later one has overtaken says nothing, not even when its request failed.
      if (n < landed.current) {
        onWay.current.delete(n);
        wish();
        return;
      }
      if (error) {
        owed(error);
        throw miss(error);
      }
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
      flushSync(() => void (ok = latest.current({ ...base(), ...kept(stored.current, base(), made!) }, `maths ${n}`)));
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
  return { p, limit, toggle, own, setOwn, typed, setTyped, wrong, commit, room, ranges, digit, show, gap, refused, line, scale, plus, times, open, dec, money, numbered, three, free, pvs, brackets, fam, families, whole, shown, lit };
}
