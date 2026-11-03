// Zeichen markieren: vowels, umlauts, consonants, the first and last letter, and up to three groups.
import { COLOURS, GROUP_COLOURS, hex, tidy, type LetterMarks, type Where } from "../../letters";
import type { Block } from "../../sheet";
import { both, syllabled } from "./words";

const KINDS = [
  ["vowels", "Vokale", "Farbe der Vokale"],
  ["umlauts", "Umlaute", "Farbe der Umlaute"],
  ["consonants", "Konsonanten", "Farbe der Konsonanten"],
  ["first", "Erster Buchstabe", "Farbe des ersten Buchstabens"],
  ["last", "Letzter Buchstabe", "Farbe des letzten Buchstabens"],
] as const;

type Kind = (typeof KINDS)[number][0];

const marksOf = (b: Block): LetterMarks => {
  const marks = syllabled(b)?.marks;
  return marks && typeof marks === "object" ? marks : {};
};

export function Letters({ sel, look, style }: { sel: Block[]; look: (props: object, key?: string) => void; style: (type: Block["type"], props: object, key?: string, only?: string[]) => void }) {
  const held = sel.filter(syllabled);
  if (!held.length) return null;
  const apply = both(held, look, style);
  const base = () => marksOf(held[0]);
  const write = (next: LetterMarks, key: string) => {
    const stored = tidy(next);
    apply(stored ? { marks: stored } : { marks: undefined }, key);
  };
  const on = (key: Kind) => held.every((b) => !!hex(marksOf(b)[key]));
  const groups = (base().groups ?? []).slice(0, 3);
  return (
    <>
      <h2>Zeichen</h2>
      {KINDS.map(([key, label, colour]) => (
        <span key={key}>
          <button className={on(key) ? "on" : ""} aria-pressed={on(key)} onClick={() => write({ ...base(), [key]: on(key) ? undefined : COLOURS[key] }, `marks-${key}`)}>
            {label}
          </button>
          {on(key) && (
            <label>
              {colour}
              <input type="color" value={hex(base()[key]) ?? COLOURS[key]} onChange={(e) => write({ ...base(), [key]: e.target.value }, `marks-${key}`)} />
            </label>
          )}
        </span>
      ))}
      {groups.map((group, i) => (
        <span key={i}>
          <label>
            {`Buchstaben ${i + 1}`}
            <input value={group.letters} onChange={(e) => write({ ...base(), groups: groups.map((g, j) => (j === i ? { ...g, letters: e.target.value } : g)) }, `marks-letters-${i}`)} />
          </label>
          <label>
            {`Stelle ${i + 1}`}
            <select value={group.where} onChange={(e) => write({ ...base(), groups: groups.map((g, j) => (j === i ? { ...g, where: e.target.value as Where } : g)) }, `marks-where-${i}`)}>
              <option value="any">Überall</option>
              <option value="start">Wortanfang</option>
              <option value="end">Wortende</option>
            </select>
          </label>
          <label>
            {`Farbe der Gruppe ${i + 1}`}
            <input type="color" value={hex(group.color) ?? COLOURS.vowels} onChange={(e) => write({ ...base(), groups: groups.map((g, j) => (j === i ? { ...g, color: e.target.value } : g)) }, `marks-group-${i}`)} />
          </label>
          <button onClick={() => write({ ...base(), groups: groups.filter((_, j) => j !== i) }, "marks-drop")}>{`Gruppe ${i + 1} entfernen`}</button>
        </span>
      ))}
      {groups.length < 3 && (
        <button onClick={() => write({ ...base(), groups: [...groups, { letters: "", where: "any", color: GROUP_COLOURS[groups.length] }] }, "marks-add")}>
          Buchstabengruppe
        </button>
      )}
    </>
  );
}
