// The maths blocks of the library "Mathe-Blöcke": each one's name, its group, the other words a search finds it by,
// and the block a click adds. A new block type gets its card, with its picture, from one line here.
import { INSERTS, type Fresh } from "../../insert";

export type Entry = { label: string; words: string; make: (seed: number) => Fresh };

// The groups in the order they show, each with its blocks.
export const LIBRARY: { name: string; entries: Entry[] }[] = [
  {
    name: "Rechnen",
    entries: [
      { label: "Zahlenmauer", words: "mauer steine addieren plus", make: INSERTS.zahlenmauer },
      { label: "Zahlenhaus", words: "haus zerlegen verliebte zahlen", make: INSERTS.zahlenhaus },
      { label: "Zahlenkette", words: "kette folge rechenkette", make: INSERTS.zahlenkette },
      { label: "Rechendreieck", words: "dreieck", make: INSERTS.rechendreieck },
      { label: "Rechenrad", words: "rad kreis einmaleins", make: INSERTS.rechenrad },
      { label: "Rechentabelle", words: "tabelle plustabelle maltabelle", make: INSERTS.rechentabelle },
      { label: "Pfeilbild", words: "pfeil pfeile maschine", make: INSERTS.pfeilbild },
      { label: "Operatorfeld", words: "operator maschine rechenmaschine", make: INSERTS.operatorfeld },
      { label: "Malquadrat", words: "mal quadrat einmaleins malkreuz multiplizieren", make: INSERTS.malquadrat },
      { label: "Halbschriftlich rechnen", words: "schrittweise rechenweg", make: INSERTS.halbschriftlich },
      { label: "Textaufgaben", words: "sachaufgabe sachaufgaben sachrechnen rechengeschichte text", make: INSERTS.textaufgabe },
      { label: "Formel", words: "bruch brüche term gleichung", make: INSERTS.formula },
    ],
  },
  {
    name: "Zahlen verstehen",
    entries: [
      { label: "Zehnerfeld", words: "zwanzigerfeld punkte plättchen menge", make: INSERTS.zehnerfeld },
      { label: "Hunderterfeld", words: "hundertertafel hunderter tafel", make: INSERTS.hunderterfeld },
      { label: "Zahlenstrahl", words: "strahl zahlenstrich rechenstrich", make: INSERTS.zahlenstrahl },
      { label: "Stellenwert-Bild", words: "stellenwert dienes würfel stangen platten zehner einer", make: INSERTS.stellenwertbild },
      { label: "Stellenwerttafel", words: "stellenwert stellentafel zehner einer hunderter", make: INSERTS.stellenwerttafel },
      { label: "Zahlzerlegung", words: "zerlegen stellenwert", make: INSERTS.zahlzerlegung },
      { label: "Zerlegungsfeld", words: "zerlegen zerlegung", make: INSERTS.zerlegungsfeld },
    ],
  },
  {
    name: "Geometrie und Größen",
    entries: [
      { label: "Uhr", words: "uhr lesen uhrzeit zeit stunde minute", make: INSERTS.uhr },
      { label: "Geobrett", words: "geometrie figuren nagelbrett", make: INSERTS.geobrett },
      { label: "Karofeld", words: "karo kästchen spiegeln symmetrie zeichnen muster", make: INSERTS.karofeld },
      { label: "Diagramm", words: "säulen balken daten strichliste", make: INSERTS.diagramm },
    ],
  },
  {
    name: "Knobeln und Kontrolle",
    entries: [
      { label: "Magisches Quadrat", words: "zauberquadrat knobeln", make: INSERTS.magischesquadrat },
      { label: "Selbstkontrolle", words: "lösungswort kontrolle prüfen", make: INSERTS.selbstkontrolle },
      { label: "Lösungsfeld", words: "antwort lösung kästchen", make: INSERTS.loesungsfeld },
    ],
  },
];

// The groups with the entries a search leaves: every word typed stands in the name or among the other words.
export function found(query: string) {
  const asked = query.toLowerCase().split(/\s+/).filter(Boolean);
  return LIBRARY.map((g) => ({
    name: g.name,
    entries: g.entries.filter((e) => asked.every((w) => `${e.label} ${e.words}`.toLowerCase().includes(w))),
  })).filter((g) => g.entries.length);
}
