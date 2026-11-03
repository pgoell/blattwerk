// Our own texts for the Textaufgaben. A story names the operation it is written for. The generator
// fills {a} {b} {c} {m} {r}. Nothing here is drawn by an image model.

import type { TextOp, Theme } from "./props";

export type Story = {
  id: string;
  theme: Theme;
  ops: TextOp[];
  clock?: "punkt" | "dauer";
  text: string;
  frage: string;
  rechnung: string;
  antwort: string;
};

const M = "\u2212";

export const STORIES: Story[] = [
  { id: "sach-plus", theme: "sach", ops: ["+"], text: "Im Stall stehen {a} Schafe. Am Morgen kommen {b} Schafe dazu.", frage: "Wie viele Schafe stehen jetzt im Stall?", rechnung: "{a} + {b} = {r}", antwort: "Im Stall stehen {r} Schafe." },
  { id: "sach-minus", theme: "sach", ops: ["-"], text: "Auf dem Parkplatz stehen {a} Autos. {b} Autos fahren weg.", frage: "Wie viele Autos stehen noch da?", rechnung: `{a} ${M} {b} = {r}`, antwort: "Es stehen noch {r} Autos da." },
  { id: "sach-mal", theme: "sach", ops: ["*"], text: "Lena kauft {a} Packungen. In jeder Packung sind {b} Kekse.", frage: "Wie viele Kekse kauft Lena?", rechnung: "{a} · {b} = {r}", antwort: "Lena kauft {r} Kekse." },
  { id: "sach-div", theme: "sach", ops: [":"], text: "{a} Bonbons werden an {b} Kinder verteilt, jedes bekommt gleich viele.", frage: "Wie viele Bonbons bekommt ein Kind?", rechnung: "{a} : {b} = {r}", antwort: "Ein Kind bekommt {r} Bonbons." },
  { id: "sach-plus-plus", theme: "sach", ops: ["+", "+"], text: "Im Stall stehen {a} Schafe. Es kommen {b} dazu und später noch {c}.", frage: "Wie viele Schafe stehen am Ende im Stall?", rechnung: "{a} + {b} = {m}\n{m} + {c} = {r}", antwort: "Am Ende stehen {r} Schafe im Stall." },
  { id: "sach-plus-minus", theme: "sach", ops: ["+", "-"], text: "Im Stall stehen {a} Schafe. Es kommen {b} dazu und danach gehen {c} weg.", frage: "Wie viele Schafe stehen dann im Stall?", rechnung: `{a} + {b} = {m}\n{m} ${M} {c} = {r}`, antwort: "Dann stehen {r} Schafe im Stall." },
  { id: "kurz-plus", theme: "kurz", ops: ["+"], text: "Mia hat {a} Stifte und bekommt {b} dazu.", frage: "Wie viele Stifte hat Mia jetzt?", rechnung: "{a} + {b} = {r}", antwort: "Mia hat {r} Stifte." },
  { id: "kurz-minus", theme: "kurz", ops: ["-"], text: "Tim hat {a} Murmeln und gibt {b} ab.", frage: "Wie viele Murmeln hat Tim noch?", rechnung: `{a} ${M} {b} = {r}`, antwort: "Tim hat noch {r} Murmeln." },
  { id: "kurz-mal", theme: "kurz", ops: ["*"], text: "Es gibt {a} Tüten mit je {b} Äpfeln.", frage: "Wie viele Äpfel sind es?", rechnung: "{a} · {b} = {r}", antwort: "Es sind {r} Äpfel." },
  { id: "kurz-div", theme: "kurz", ops: [":"], text: "{a} Pflaumen werden auf {b} Teller gelegt.", frage: "Wie viele Pflaumen liegen auf einem Teller?", rechnung: "{a} : {b} = {r}", antwort: "Auf einem Teller liegen {r} Pflaumen." },
  { id: "kurz-plus-plus", theme: "kurz", ops: ["+", "+"], text: "Noah hat {a} Punkte, bekommt {b} dazu und dann noch {c}.", frage: "Wie viele Punkte hat Noah am Ende?", rechnung: "{a} + {b} = {m}\n{m} + {c} = {r}", antwort: "Noah hat {r} Punkte." },
  { id: "kurz-plus-minus", theme: "kurz", ops: ["+", "-"], text: "Noah hat {a} Punkte, bekommt {b} dazu und gibt dann {c} ab.", frage: "Wie viele Punkte hat Noah dann?", rechnung: `{a} + {b} = {m}\n{m} ${M} {c} = {r}`, antwort: "Noah hat dann {r} Punkte." },
  { id: "kurz-minus-plus", theme: "kurz", ops: ["-", "+"], text: "Noah hat {a} Punkte, gibt {b} ab und bekommt dann {c}.", frage: "Wie viele Punkte hat Noah dann?", rechnung: `{a} ${M} {b} = {m}\n{m} + {c} = {r}`, antwort: "Noah hat dann {r} Punkte." },
  { id: "kurz-minus-minus", theme: "kurz", ops: ["-", "-"], text: "Noah hat {a} Punkte, gibt {b} ab und dann noch {c}.", frage: "Wie viele Punkte hat Noah noch?", rechnung: `{a} ${M} {b} = {m}\n{m} ${M} {c} = {r}`, antwort: "Noah hat noch {r} Punkte." },
  { id: "kurz-mal-plus", theme: "kurz", ops: ["*", "+"], text: "{a} Schachteln haben je {b} Stifte. {c} Stifte kommen dazu.", frage: "Wie viele Stifte sind es dann?", rechnung: "{a} · {b} = {m}\n{m} + {c} = {r}", antwort: "Es sind {r} Stifte." },
  { id: "kurz-div-div", theme: "kurz", ops: [":", ":"], text: "{a} Perlen werden auf {b} Kinder verteilt, jedes teilt seinen Teil durch {c}.", frage: "Wie viele Perlen hat ein Kind am Ende?", rechnung: "{a} : {b} = {m}\n{m} : {c} = {r}", antwort: "Ein Kind hat {r} Perlen." },
  { id: "raetsel-plus", theme: "raetsel", ops: ["+"], text: "Rate die Zahl: {a} und {b} werden zusammengezählt.", frage: "Welche Zahl kommt heraus?", rechnung: "{a} + {b} = {r}", antwort: "Die Zahl ist {r}." },
  { id: "raetsel-minus", theme: "raetsel", ops: ["-"], text: "Rate die Zahl: von {a} wird {b} weggenommen.", frage: "Welche Zahl bleibt?", rechnung: `{a} ${M} {b} = {r}`, antwort: "Die Zahl ist {r}." },
  { id: "raetsel-mal", theme: "raetsel", ops: ["*"], text: "Rate die Zahl: {a} mal {b}.", frage: "Welche Zahl kommt heraus?", rechnung: "{a} · {b} = {r}", antwort: "Die Zahl ist {r}." },
  { id: "raetsel-div", theme: "raetsel", ops: [":"], text: "Rate die Zahl: {a} geteilt durch {b}.", frage: "Welche Zahl kommt heraus?", rechnung: "{a} : {b} = {r}", antwort: "Die Zahl ist {r}." },
  { id: "raetsel-plus-plus", theme: "raetsel", ops: ["+", "+"], text: "Rate die Zahl: erst {a} plus {b}, dann noch {c} dazu.", frage: "Welche Zahl kommt am Ende heraus?", rechnung: "{a} + {b} = {m}\n{m} + {c} = {r}", antwort: "Die Zahl ist {r}." },
  { id: "zeit-punkt-plus", theme: "zeit", clock: "punkt", ops: ["+"], text: "Der Film beginnt um {a} Uhr und dauert {b} Minuten.", frage: "Wann ist der Film zu Ende?", rechnung: "{a} + {b} min = {r}", antwort: "Um {r} Uhr." },
  { id: "zeit-punkt-minus", theme: "zeit", clock: "punkt", ops: ["-"], text: "Der Film ist um {a} Uhr zu Ende. Er hat {b} Minuten gedauert.", frage: "Wann hat der Film begonnen?", rechnung: `{a} ${M} {b} min = {r}`, antwort: "Um {r} Uhr." },
  { id: "zeit-punkt-plus-plus", theme: "zeit", clock: "punkt", ops: ["+", "+"], text: "Die Schule beginnt um {a} Uhr. Die erste Stunde dauert {b} Minuten, die Pause danach {c} Minuten.", frage: "Wann beginnt die zweite Stunde?", rechnung: "{a} + {b} min = {m}\n{m} + {c} min = {r}", antwort: "Um {r} Uhr." },
  { id: "zeit-dauer", theme: "zeit", clock: "dauer", ops: ["-"], text: "Lea zählt die Minuten von {a} Uhr bis {b} Uhr.", frage: "Wie viele Minuten sind das?", rechnung: `{b} ${M} {a} = {r}`, antwort: "{r} Minuten." },
  { id: "zeit-dauer-plus", theme: "zeit", clock: "dauer", ops: ["+", "+"], text: "Tom liest {a} Minuten und danach noch {b} Minuten. Dann liest er noch {c} Minuten.", frage: "Wie viele Minuten liest Tom insgesamt?", rechnung: "{a} + {b} = {m}\n{m} + {c} = {r}", antwort: "Tom liest {r} Minuten." },
  { id: "geld-plus", theme: "geld", ops: ["+"], text: "Ein Heft kostet {a} € und ein Stift {b} €.", frage: "Wie viel kosten beide zusammen?", rechnung: "{a} € + {b} € = {r} €", antwort: "Beide kosten {r} €." },
  { id: "geld-minus", theme: "geld", ops: ["-"], text: "Mia hat {a} € und kauft einen Apfel für {b} €.", frage: "Wie viel Geld hat Mia danach?", rechnung: `{a} € ${M} {b} € = {r} €`, antwort: "Mia hat danach {r} €." },
  { id: "geld-mal", theme: "geld", ops: ["*"], text: "Ein Heft kostet {a} €. Mia kauft {b} Hefte.", frage: "Wie viel bezahlt Mia?", rechnung: "{a} € · {b} = {r} €", antwort: "Mia bezahlt {r} €." },
  { id: "geld-div", theme: "geld", ops: [":"], text: "Mia hat {a} € und verteilt das Geld an {b} Kinder, jedes bekommt gleich viel.", frage: "Wie viel bekommt ein Kind?", rechnung: "{a} € : {b} = {r} €", antwort: "Ein Kind bekommt {r} €." },
  { id: "geld-plus-plus", theme: "geld", ops: ["+", "+"], text: "Ein Heft kostet {a} €, ein Stift {b} € und ein Radiergummi {c} €.", frage: "Wie viel kosten alle drei?", rechnung: "{a} € + {b} € = {m} €\n{m} € + {c} € = {r} €", antwort: "Alle drei kosten {r} €." },
  { id: "geld-plus-minus", theme: "geld", ops: ["+", "-"], text: "Ein Buch kostet {a} € und der Versand {b} €. Ein Gutschein ist {c} € wert.", frage: "Wie viel bleibt zu bezahlen?", rechnung: `{a} € + {b} € = {m} €\n{m} € ${M} {c} € = {r} €`, antwort: "Es bleiben {r} €." },
];
