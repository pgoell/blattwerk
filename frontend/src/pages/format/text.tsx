// The Schrift section: face, marks, lists, trace, gaps and the words a text takes from the sheet.
import { AlignVerticalJustifyCenter, AlignVerticalJustifyEnd, AlignVerticalJustifyStart, List as Bullets, ListOrdered, TextAlignCenter, TextAlignEnd, TextAlignStart, type LucideIcon } from "lucide-react";
import { has } from "../../arrange";
import { boxed, fontOf, fromOf, parasOf, stepOf, type Align, type Block, type Doc, type List, type Valign } from "../../sheet";
import type { Marks, Picked } from "../Field";
import { Fed } from "./fed";
import { FontSelect, unknownFont } from "./font";
import { Gaps } from "./gaps";
import { Mix } from "./mix";
import { Num } from "./num";
import { Syllables } from "./syllables";
import { TraceControls } from "./trace";
import { syllabled, worded } from "./words";

const ALIGNS: [Align, string, LucideIcon][] = [["left", "Links", TextAlignStart], ["center", "Mitte", TextAlignCenter], ["right", "Rechts", TextAlignEnd]];
const LISTS: [List, string, LucideIcon][] = [["bullet", "Aufzählung", Bullets], ["number", "Nummerierung", ListOrdered]];
const VALIGNS: [Valign, string, LucideIcon][] = [["top", "Oben", AlignVerticalJustifyStart], ["middle", "Mitte", AlignVerticalJustifyCenter], ["bottom", "Unten", AlignVerticalJustifyEnd]];

export function TextPanel({
  sel, part, look, style, paint, itemize, traced, link, feed, gap, every, cell, mendWord, doc, words, toList, onHelp,
}: {
  sel: Block[];
  part?: Picked;
  look: (props: object, key?: string) => void;
  style: (type: Block["type"], props: object, key?: string, only?: string[]) => void;
  paint: (props: Marks, key?: string) => void;
  itemize: (kind: List) => void;
  traced: (props: object) => void;
  link: (on: boolean) => void;
  feed: (props: object, key?: string) => void;
  gap: (on: boolean) => void;
  every: (n: number) => void;
  cell?: number;
  mendWord: (keys: string[], counts: number[] | undefined, id: string) => void;
  doc: Doc;
  words: string[];
  toList: () => void;
  onHelp?: () => void;
}) {
  const text = sel.map(boxed).find((p) => p);
  if (!text) return null;
  const shown = { ...text, ...part?.marks };
  const kind = (part ?? parasOf(text)[0]).list;
  const texts = sel.filter((b): b is Extract<Block, { type: "text" }> => b.type === "text");
  const numbered = texts.length > 0 && texts.every((b) => stepOf(b.props.lines) > 0);
  const starts = texts.map((b) => fromOf(b.props.linesFrom));
  const start = starts.every((s) => s === starts[0]) ? starts[0] : undefined;
  return (
    <>
          {onHelp && (
            <button type="button" onClick={onHelp}>
              Text anpassen
            </button>
          )}
          <h2>Schrift</h2>
          <FontSelect label="Schriftart" value={fontOf(text.font)} unknown={unknownFont(sel.map((b) => boxed(b)?.font))} onChange={(font) => look({ font })} />
          <div className="seg">
            <button aria-label="Schrift kleiner" onClick={() => look({ size: Math.max(8, text.size - 2) })}>−</button>
            <output>{text.size} pt</output>
            <button aria-label="Schrift größer" onClick={() => look({ size: text.size + 2 })}>＋</button>
          </div>
          <div className="seg">
            {([["bold", "Fett"], ["italic", "Kursiv"], ["underline", "Unterstrichen"]] as const).map(([prop, label]) => (
              <button key={prop} className={`${prop}${has(sel, part, prop) ? " on" : ""}`} aria-label={label} aria-pressed={has(sel, part, prop)} onClick={() => paint({ [prop]: !has(sel, part, prop) })}>
                {label[0]}
              </button>
            ))}
          </div>
          <div className="seg">
            {LISTS.map(([value, label, Icon]) => (
              <button key={value} className={kind === value ? "on" : ""} aria-label={label} title={label} aria-pressed={kind === value} onClick={() => itemize(value)}>
                <Icon size={14} aria-hidden />
              </button>
            ))}
          </div>
          <div className="seg">
            {ALIGNS.map(([value, label, Icon]) => (
              <button key={value} className={text.align === value ? "on" : ""} aria-label={label} title={label} aria-pressed={text.align === value} onClick={() => look({ align: value })}>
                <Icon size={14} aria-hidden />
              </button>
            ))}
          </div>
          <div className="seg">
            {VALIGNS.map(([value, label, Icon]) => (
              <button key={value} className={(text.valign ?? "top") === value ? "on" : ""} aria-label={label} title={label} aria-pressed={(text.valign ?? "top") === value} onClick={() => look({ valign: value })}>
                <Icon size={14} aria-hidden />
              </button>
            ))}
          </div>
          <label>
            Farbe
            <input type="color" value={shown.color ?? "#222222"} onChange={(e) => paint({ color: e.target.value }, "color")} />
          </label>
          <label>
            Zeilenabstand
            <input type="range" min={1} max={3} step={0.1} value={text.spacing ?? 1.3} onChange={(e) => look({ spacing: +e.target.value }, "spacing")} />
          </label>
          <TraceControls props={text} font={text.font} onChange={traced} />
          <Syllables key={sel.find(syllabled)?.id} sel={sel} part={part} look={look} style={style} mendWord={mendWord} doc={doc} words={words} />
          <Gaps key={`gaps-${sel.find(worded)?.id}`} sel={sel} part={part} cell={cell} look={look} style={style} gap={gap} every={every} />
          <Fed sel={sel} words={words} toList={toList} look={look} link={link} feed={feed} />
          <Mix sel={sel} look={look} words={words} />
          {/* Only texts take line numbers. Off is no key, as on a text that never had them; on starts with every fifth line. */}
          {texts.length > 0 && (
            <>
              <button className={numbered ? "on" : ""} aria-pressed={numbered} onClick={() => style("text", { lines: numbered ? undefined : 5 }, "lines")}>
                Zeilennummern
              </button>
              {numbered && (
                <div className="seg">
                  <button className={stepOf(texts[0].props.lines) === 1 ? "on" : ""} aria-pressed={stepOf(texts[0].props.lines) === 1} onClick={() => style("text", { lines: 1 }, "lines")}>
                    Jede Zeile
                  </button>
                  <button className={stepOf(texts[0].props.lines) === 5 ? "on" : ""} aria-pressed={stepOf(texts[0].props.lines) === 5} onClick={() => style("text", { lines: 5 }, "lines")}>
                    Jede 5. Zeile
                  </button>
                </div>
              )}
              {numbered && (
                <Num label="Beginnt bei" value={start} disabled={false} onCommit={(n) => Number.isInteger(n) && n >= 1 && n <= 9999 && style("text", { linesFrom: n === 1 ? undefined : n }, "linesFrom")} />
              )}
            </>
          )}
    </>
  );
}
