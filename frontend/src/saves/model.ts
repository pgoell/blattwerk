import { useSyncExternalStore } from "react";
import { catchUp, onOther, onSignedOut, signed } from "../api";
import type { Doc, MathsProps } from "../sheet";

// A maths change the session ran out on. `change` holds only what the click changed.
export type Owed = { block: string; change: Partial<MathsProps> };

// The wait after a change before it is saved. The tests set a shorter one on the page; a teacher's page has none and waits 2 s.
export const AFTER = (window as { saveAfter?: number }).saveAfter ?? 2000;

// Each sheet has one saver, and it outlives the editor: a save that is out, fails or never answers when the teacher
// has left the sheet is still seen through, and no load waits for it. The editor says what the sheet holds now and
// reads from here whether that is saved.
export type Kept = { doc: Doc; title: string };
export type Saver = {
  id: number;
  owner: number;
  // The version every save is based on. It moves to a version of the server only where the server confirmed a save
  // from here or holds a document sent from here, where the sheet opens with no clash, or where the teacher chose
  // to overwrite. In a clash it is the version the change was made on.
  base: number;
  // What the server is known to hold, and the newest the editor has.
  saved: Kept;
  want: Kept;
  // What is on the wire, and what went with no answer since the server last confirmed a version: it may hold one of
  // those. The first and the newest are kept: the first that arrived is the one it took.
  out?: Kept;
  lost: Kept[];
  // Set when a save leaves, cleared only by an HTTP answer. A fetch the browser cancels has none: the server may
  // still hold that save, or be about to, so the tab sends nothing beside it as it shuts (#390).
  flying?: boolean;
  tries: number;
  // The server holds another device's document: saving stops until the teacher has chosen.
  clash: boolean;
  // The server refused the document for what is wrong in it: nothing of that document is sent again, the change
  // stays unsaved, until the document changes.
  refused?: { doc: Doc; problems: string[]; title?: string };
  // The session ran out: nothing goes until a login or the next visit.
  stop: boolean;
  // Changes the server did not get because the session ran out, to be redone by the sheet's editor after the login.
  owed?: Owed[];
  // The sheet was deleted elsewhere: nothing is sent any more, and what the editor shows is kept until the teacher
  // has chosen, to keep it as a new sheet or to drop it. `choice` says how the first of the two stands.
  gone: boolean;
  choice?: "busy" | "failed";
  // The change last sent as a sheet kept as new, whose answer may not have come.
  asked?: Kept;
  // What the server refused in the sheet kept as new, where its answer was a refusal.
  choiceProblems?: string[];
  // Another account took over: nothing of this one is sent or heard any more.
  dead: boolean;
  // Whether the sheet's editor is there.
  open: boolean;
  // Whether a record of this saver lies in the browser's store.
  kept: boolean;
  // Unsaved for over a second.
  late: boolean;
  // The clocks: to the next save, to `late`, and to the store, which has each change within a second.
  timer?: ReturnType<typeof setTimeout>;
  slow?: ReturnType<typeof setTimeout>;
  note?: ReturnType<typeof setTimeout>;
  idle: (() => void)[];
};
// What the browser keeps of an unsaved change, for the next visit. `title` only where it changed here, `sent` only
// where a document other than `doc` is on the wire or went without an answer: the server may hold any of them.
// `name` is the title the server held last: a sheet deleted elsewhere is named by it at the next start. A record
// written before there was one has none.
// `lists` marks a record of a build that knows the Lernwörter: one without it names no list because its build
// dropped the sheet's, not because the teacher took it away.
// `asked` is the change a keep of a sheet deleted elsewhere last sent as a new sheet, whose answer may not have come:
// a press after a reload finds that sheet rather than making a second one.
export type Record = { owner: number; base: number; doc: Doc; title?: string; sent?: Doc[]; name?: string; lists?: boolean; asked?: Kept };
export type Save = { id: number; owner: number; title: string; saved: Kept; unsaved: boolean; failed: boolean; stopped: boolean; clash: boolean; refused?: string[]; late: boolean; gone: boolean; open: boolean; choice?: "busy" | "failed"; choiceProblems?: string[] };

export const savers = new Map<number, Saver>();
// Who is signed in, as the app said last, and what the app does when a save finds the session gone. A login in
// another tab changes the session and not `me`, so whose a sheet or a 404 is, the answer itself says: each names the
// user it was served for.
export let me: number | undefined;
export const setAccount = (owner?: number) => void (me = owner);
// The guard itself lies in api.ts, which a script with no window can load too.
export { onOther, onSignedOut, signed };
// A sheet served for another account than this window holds: the app asks who is signed in, and goes on as that one.
export const served = (by?: number) => void (by !== undefined && by !== me && catchUp());
const heard = new Set<() => void>();
// `landed` counts the saves the server took: the list asks anew at each.
let shot = { list: [] as Save[], landed: 0 };
export const key = (id: number) => `unsaved:${id}`;
export const same = (a: Doc, b: Doc) => JSON.stringify(a) === JSON.stringify(b);
// A save that got no answer counts too: the server may hold it though the teacher has undone it since. So does a
// clash: the server holds another device's document, whatever the editor is back at. And of a sheet deleted
// elsewhere the server holds nothing: all the editor shows is unsaved, also where it is back at what was saved.
export const unsaved = (s: Saver) => s.gone || !!s.out || s.clash || s.lost.length > 0 || !!s.owed?.length || s.want.doc !== s.saved.doc || s.want.title !== s.saved.title;
// The refusal that stands: for the document the saver holds now, and only while it is the one refused.
export const refusal = (s: Saver) => (s.refused && same(s.refused.doc, s.want.doc) ? s.refused : undefined);
// While the document is refused, the title goes alone only where it changed, and not as one the server refused.
export const waits = (s: Saver) => s.want.title === s.saved.title || s.want.title === refusal(s)?.title;
// The saver's end: nothing of it is sent, heard or written any more.
export function kill(s: Saver) {
  s.dead = true;
  for (const clock of [s.timer, s.slow, s.note]) clearTimeout(clock);
  savers.delete(s.id);
}

// Tells who reads the savers, where what they read has changed: the editor draws anew only then.
export function tell(landed = 0) {
  const list = [...savers.values()].map((s) => ({ id: s.id, owner: s.owner, title: s.want.title, saved: s.saved, unsaved: unsaved(s), failed: s.tries > 0 || s.stop || s.gone || !!refusal(s), stopped: s.stop, clash: s.clash, refused: refusal(s)?.problems, late: s.late, gone: s.gone, open: s.open, choice: s.choice, choiceProblems: s.choiceProblems }));
  const was = shot.list;
  if (!landed && list.length === was.length && list.every((s, i) => (Object.keys(s) as (keyof Save)[]).every((k) => s[k] === was[i][k]))) return;
  shot = { list, landed: shot.landed + landed };
  heard.forEach((hear) => hear());
}
const listen = (hear: () => void) => {
  heard.add(hear);
  return () => void heard.delete(hear);
};
export const useSaves = () => useSyncExternalStore(listen, () => shot);

// Writes the unsaved change into the browser's store, or takes it out once all is saved. The key is the sheet's:
// a record another account left there stays until this one has a change of its own to keep, which then takes its
// place. That account's sheet is not this one's, so the two meet only where the server gave an id anew.
export function kept(id: number): Record | null {
  try {
    return JSON.parse(localStorage.getItem(key(id)) ?? "null");
  } catch {
    // Unreadable: as if there were none.
    return null;
  }
}
export function keep(s: Saver) {
  try {
    if (unsaved(s)) {
      const sent = [...s.lost, s.out].flatMap((k) => (k && k.doc !== s.want.doc ? [k.doc] : []));
      const record: Record = { owner: s.owner, base: s.base, doc: s.want.doc, title: s.want.title === s.saved.title ? undefined : s.want.title, sent: sent.length ? sent : undefined, name: s.saved.title, lists: true, asked: s.asked };
      localStorage.setItem(key(s.id), JSON.stringify(record));
      s.kept = true;
    } else if (s.kept) {
      localStorage.removeItem(key(s.id));
      s.kept = false;
    }
  } catch {
    // The store is full or shut: the change lives on in this window alone.
  }
}


// The sheet's saver and its kept change go: the teacher deleted the sheet here, chose the other version of a clash,
// or chose what becomes of a sheet deleted elsewhere. The list asks anew after that last one.
export function forget(id: number) {
  const s = savers.get(id);
  if (s) kill(s);
  if (s?.kept || kept(id)?.owner === me) localStorage.removeItem(key(id));
  tell(s?.gone ? 1 : 0);
}
// Whether the sheet was deleted elsewhere and waits for the teacher's choice, as of this moment.
export const isGone = (id: number) => !!savers.get(id)?.gone;
export const inClash = (id: number) => !!savers.get(id)?.clash;
