import { useSyncExternalStore } from "react";
import { api, catchUp, countLogin, onOther, onSignedOut, showLogin as signedOut, signed, type Refusal } from "./api";
import { read, type Doc, type MathsProps, type Sheet } from "./sheet";

// The wait after a change before it is saved. The tests set a shorter one on the page; a teacher's page has none and waits 2 s.
const AFTER = (window as { saveAfter?: number }).saveAfter ?? 2000;

// Each sheet has one saver, and it outlives the editor: a save that is out, fails or never answers when the teacher
// has left the sheet is still seen through, and no load waits for it. The editor says what the sheet holds now and
// reads from here whether that is saved.
export type Kept = { doc: Doc; title: string };
type Saver = {
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
type Record = { owner: number; base: number; doc: Doc; title?: string; sent?: Doc[]; name?: string; lists?: boolean; asked?: Kept };
export type Save = { id: number; owner: number; title: string; saved: Kept; unsaved: boolean; failed: boolean; stopped: boolean; clash: boolean; refused?: string[]; late: boolean; gone: boolean; open: boolean; choice?: "busy" | "failed"; choiceProblems?: string[] };

const savers = new Map<number, Saver>();
// Who is signed in, as the app said last, and what the app does when a save finds the session gone. A login in
// another tab changes the session and not `me`, so whose a sheet or a 404 is, the answer itself says: each names the
// user it was served for.
let me: number | undefined;
// The guard itself lies in api.ts, which a script with no window can load too.
export { onOther, onSignedOut, signed };
// A sheet served for another account than this window holds: the app asks who is signed in, and goes on as that one.
export const served = (by?: number) => void (by !== undefined && by !== me && catchUp());
const heard = new Set<() => void>();
// `landed` counts the saves the server took: the list asks anew at each.
let shot = { list: [] as Save[], landed: 0 };
const key = (id: number) => `unsaved:${id}`;
const same = (a: Doc, b: Doc) => JSON.stringify(a) === JSON.stringify(b);
// A save that got no answer counts too: the server may hold it though the teacher has undone it since. So does a
// clash: the server holds another device's document, whatever the editor is back at. And of a sheet deleted
// elsewhere the server holds nothing: all the editor shows is unsaved, also where it is back at what was saved.
const unsaved = (s: Saver) => s.gone || !!s.out || s.clash || s.lost.length > 0 || !!s.owed?.length || s.want.doc !== s.saved.doc || s.want.title !== s.saved.title;
// The refusal that stands: for the document the saver holds now, and only while it is the one refused.
const refusal = (s: Saver) => (s.refused && same(s.refused.doc, s.want.doc) ? s.refused : undefined);
// While the document is refused, the title goes alone only where it changed, and not as one the server refused.
const waits = (s: Saver) => s.want.title === s.saved.title || s.want.title === refusal(s)?.title;
// The saver's end: nothing of it is sent, heard or written any more.
function kill(s: Saver) {
  s.dead = true;
  for (const clock of [s.timer, s.slow, s.note]) clearTimeout(clock);
  savers.delete(s.id);
}

// Tells who reads the savers, where what they read has changed: the editor draws anew only then.
function tell(landed = 0) {
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
function kept(id: number): Record | null {
  try {
    return JSON.parse(localStorage.getItem(key(id)) ?? "null");
  } catch {
    // Unreadable: as if there were none.
    return null;
  }
}
function keep(s: Saver) {
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

// An answer that has not come after 20 s counts as none. By a timer of the page: a test's clock moves that one.
export function ask<T>(path: string, init?: RequestInit) {
  const stop = new AbortController();
  const limit = setTimeout(() => stop.abort(), 20000);
  return signed(api<T>(path, { ...init, signal: stop.signal })).finally(() => clearTimeout(limit));
}
// A sheet as its editor asks for it: null where it is not there, "failed" where the server could not say. An
// address that names no number, a 422, has no sheet either. Never refused, for the editor's script may come to
// listen after the answer.
export const get = (id: string) => ask<Sheet>(`/sheets/${id}`).catch((e: Error) => (e.message === "404" || e.message === "422" ? null : ("failed" as const)));

function plan(s: Saver, ms: number) {
  clearTimeout(s.timer);
  s.timer = setTimeout(() => send(s), ms);
}

// An HTTP status, or a 401 from a session that has since changed. Anything else is the browser dropping the fetch.
const answered = (e: Refusal) => /^\d+$/.test(e.message) || e.message === "stale";

// One save of a sheet at a time, always based on the saver's version. `closing` is the window that shuts.
function send(s: Saver, closing = false) {
  clearTimeout(s.timer);
  // The save under way was cancelled on the way out. Another on this version would land beside it (#390).
  if (closing && s.flying) return;
  if (s.dead || s.out || s.clash || s.stop || s.gone || !unsaved(s)) return;
  // A refused document is not sent again. A title changed since still goes, alone: the server keeps the document.
  const held = refusal(s);
  if (held && waits(s)) return;
  const now = (s.out = s.want);
  // The title goes along only when it changed here, so a rename from the list stays.
  const named = now.title === s.saved.title ? {} : { title: now.title.trim() || "Unbenanntes Blatt" };
  // The Lernwörter always go along, an empty list for none: a document that names no list comes from a window on a
  // build from before them, and the server then keeps the list it holds.
  const body = JSON.stringify(held ? named : { doc: { ...now.doc, words: now.doc.words ?? [] }, version: s.base, ...named });
  // `keepalive` lets a save outlive the window. The browser sends no such request over 64 KiB, so a larger sheet
  // goes without it: left for another page of the app, it arrives all the same.
  const keepalive = (closing || !s.open) && new Blob([body]).size < 60 * 1024;
  s.flying = true;
  s.slow ??= setTimeout(() => {
    s.late = true;
    tell();
  }, 1000);
  keep(s);
  tell();
  ask<Sheet>(`/sheets/${s.id}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body, keepalive }).then(
    (sheet) => {
      s.flying = false;
      if (s.dead) return;
      if (held) s.saved = { doc: s.saved.doc, title: now.title };
      else {
        s.base = sheet.version;
        s.saved = now;
        s.lost = [];
        announceSaved(s.id, sheet.version);
      }
      s.tries = 0;
      settle(s, 1);
    },
    (e: Refusal) => {
      if (answered(e)) s.flying = false;
      return fail(s, now, e);
    },
  );
}

async function fail(s: Saver, now: Kept, e: Refusal) {
  if (s.dead) return;
  if (e.message === "409") {
    // The server holds a newer version. It may be this browser's own save, whose answer never came: then it holds
    // a document sent from here, and saving goes on from its version.
    const sheet = await ask<Sheet>(`/sheets/${s.id}`).catch((e: Refusal) => e);
    if (s.dead) return;
    if (!(sheet instanceof Error)) {
      const ours = [now, ...s.lost].find((k) => same(k.doc, sheet.doc));
      if (ours) {
        s.base = sheet.version;
        s.saved = ours;
        s.tries = 0;
      } else s.clash = true;
      s.lost = [];
      return settle(s, ours ? 1 : 0);
    }
    e = sheet;
  } else if (e.problems) {
    // The server answered and holds none of this document: it is kept, and not sent again until it changes.
    // A title that went alone and was refused too waits for a change of its own, or of the document (#687).
    const alone = !!s.refused && same(now.doc, s.refused.doc);
    s.refused = alone ? { ...s.refused!, title: now.title } : { doc: now.doc, problems: e.problems };
    s.tries = 0;
    return settle(s);
  // A title that went alone took no document along: the server holds none of `now` then.
  } else if (!["401", "404", "stale"].includes(e.message) && !s.lost.includes(now) && !(s.refused && now.doc === s.refused.doc)) s.lost = [...s.lost.slice(0, 1), now];
  // Another account's sheet is as missing as a deleted one: only a 404 served for the owner means the sheet is gone.
  // One that names nobody is a failure like any other. The saver of a sheet that is gone stays, with the change and
  // its record, until the teacher has chosen, and the list asks anew: it shows the sheet no more.
  if (e.by === s.owner) {
    s.gone = true;
    s.lost = [];
    s.tries = 0;
  } else if (e.message === "401" || e.by !== undefined) s.stop = true;
  else s.tries++;
  settle(s, s.gone ? 1 : 0);
  // Another tab may have taken its choice before this one was gone: that choice is applied now.
  const heard = s.gone && heardOf(s.id);
  if (heard && !s.dead && s.choice !== "busy") endWith(s, heard);
  // The session is gone: the app shows the login, and the login brings the saver back to work.
  if (s.stop) signedOut();
}

// After each answer: what is still unsaved goes next. At once when the editor is gone, two seconds after the last
// change when it is there, and after a failure in 2 s, then 4, 8, up to 30.
function settle(s: Saver, landed = 0) {
  s.out = undefined;
  if (!unsaved(s)) {
    clearTimeout(s.slow);
    s.slow = undefined;
    s.late = false;
  }
  keep(s);
  tell(landed);
  s.idle.splice(0).forEach((done) => done());
  // A refused document waits for a change; a title changed meanwhile still goes.
  if (!unsaved(s) || s.clash || s.stop || s.gone || (refusal(s) && waits(s))) return;
  if (s.tries) plan(s, Math.min(2000 * 2 ** (s.tries - 1), 30000));
  else if (s.open) plan(s, AFTER);
  else send(s);
}

// The sheet as the editor shows it, given the server's answer. A saver with an unsaved change, or one ahead of this
// answer, goes on as it is: the sheet opened again before its save landed shows the change, and the next save is
// based on what that one brings. Else the saver starts from the answer, and a change the browser kept for this
// account comes back: as an unsaved one where the server still holds what it was based on or a save from here, and
// as a clash where the sheet was changed elsewhere meanwhile. The account is the one the answer names.
export function open(sheet: Sheet): Sheet {
  const owner = sheet.user_id;
  served(owner);
  let s = savers.get(sheet.id);
  if (!s || s.owner !== owner || !(unsaved(s) || s.base > sheet.version)) {
    if (s) kill(s);
    // `read` brings an old document up to date; that is no change.
    const saved = { doc: read(sheet.doc), title: sheet.title };
    s = { id: sheet.id, owner, base: sheet.version, saved, want: saved, lost: [], tries: 0, clash: false, stop: false, gone: false, dead: false, open: false, kept: false, late: false, idle: [] };
    savers.set(s.id, s);
    // The clicks a tab before owed for this teacher: the editor redoes them when it opens.
    s.owed = owedIn(sheet.id)?.filter((e) => e.owner === owner).map(({ block, change }) => ({ block, change }));
    const record = handed.get(s.id) ?? kept(s.id);
    handed.delete(s.id);
    // A change kept by a build from before the Lernwörter takes the sheet's list: so it neither deletes the list
    // when it is sent, nor reads as another version for lacking it.
    if (record && !record.lists && record.doc && sheet.doc.words) {
      const listed = (doc: Doc) => ("words" in doc ? doc : { ...doc, words: sheet.doc.words });
      record.doc = listed(record.doc);
      record.sent = record.sent?.map(listed);
    }
    if (record?.owner === owner) {
      const ours = sheet.version > record.base && (record.sent?.some((doc) => same(doc, sheet.doc)) || same(record.doc, sheet.doc));
      const title = record.title ?? sheet.title;
      if (!same(record.doc, sheet.doc) || title !== sheet.title) s.want = { doc: read(record.doc), title };
      s.clash = unsaved(s) && sheet.version !== record.base && !ours;
      // In a clash the saver stays on the version the change was made on, and so does the record, which every
      // road writes from the saver: the next visit reads the clash anew, however many there are. On the server's
      // version it would read none at the visit after this one, and send the change over the other device's sheet.
      if (s.clash) s.base = record.base;
      // A save that went from the tab before may still arrive, or has and the answer here is older: the saver
      // knows those documents as this browser's own when a save of its own is turned down. Once the server is
      // past the version they were based on, it takes none of them any more. They keep the saver unsaved also
      // where the teacher has undone the change: what the editor shows is sent again, as the tab before would have.
      if (sheet.version === record.base) s.lost =(record.sent ?? []).map((doc) => ({ doc, title: sheet.title }));
      s.kept = true;
      keep(s);
    }
  }
  // The server gave the sheet, so it is there: no id is given twice, and only an answer older than the delete
  // comes here for a sheet that is gone. The next save finds it gone again.
  s.stop = s.gone = false;
  send(s);
  tell();
  return { ...sheet, doc: s.want.doc, title: s.want.title };
}

// The editor is there. Gives what it calls as it goes, with what the sheet holds last: that is kept and sent at
// once, or right after the save under way. An editor whose saver was started over meanwhile has nothing to say.
export function attach(id: number, last: () => Kept) {
  const s = savers.get(id);
  if (!s) return;
  s.open = true;
  tell();
  return () => {
    if (s.dead) return;
    const want = last();
    s.want = s.want.doc === want.doc && s.want.title === want.title ? s.want : want;
    s.open = false;
    keep(s);
    send(s);
    tell();
  };
}
// A maths change the session ran out on: kept by the saver, red bar at once, redone by the editor after the login.
// `change` holds only what the click changed: the redo lays it over the block as it is then.
export type Owed = { block: string; change: Partial<MathsProps> };
// The browser keeps the owed clicks under a key of their own, each with its teacher: every tab adds to the list
// there, so no tab's record of its document drops another tab's click (#890). Null where the store cannot be read.
const owedKey = (id: number) => `owed:${id}`;
function owedIn(id: number): (Owed & { owner: number })[] | null {
  try {
    return JSON.parse(localStorage.getItem(owedKey(id)) ?? "[]");
  } catch {
    return null;
  }
}
function owedTo(id: number, list: (Owed & { owner: number })[]) {
  try {
    if (list.length) localStorage.setItem(owedKey(id), JSON.stringify(list));
    else localStorage.removeItem(owedKey(id));
  } catch {
    // The store is full or shut: the click lives on in this window alone.
  }
}
// `stop` where the session ran out; a redo that failed for another reason stays owed and lets the saves go on.
export function owe(id: number, entry: Owed, stop = true) {
  const s = savers.get(id);
  if (!s) return;
  s.owed = [...(s.owed ?? []), entry];
  owedTo(id, [...(owedIn(id) ?? []), { ...entry, owner: s.owner }]);
  if (stop) s.stop = true;
  keep(s);
  tell();
}
// Hands out the owed changes of a sheet, to its owner only: another account's login gets none. The store holds
// every tab's clicks, this one's too, so where it can be read it is the list, and a click another tab has taken
// is not redone here again.
export function takeOwed(id: number, owner: number): Owed[] {
  const s = savers.get(id);
  if (!s || s.owner !== owner) return [];
  const all = owedIn(id);
  const list = all ? all.filter((e) => e.owner === owner).map(({ block, change }) => ({ block, change })) : (s.owed ?? []);
  if (all) owedTo(id, all.filter((e) => e.owner !== owner));
  s.owed = undefined;
  keep(s);
  tell();
  return list;
}

// The editor says what the sheet holds after each change.
export function set(id: number, want: Kept) {
  const s = savers.get(id);
  if (!s || (s.want.doc === want.doc && s.want.title === want.title)) return;
  s.want = want;
  // A save that failed has a clock of its own. An undo back to what is saved leaves nothing to keep.
  if (!s.tries) plan(s, AFTER);
  if (!unsaved(s)) keep(s);
  // The store has the change within a second, also while nothing can be sent: a save is out, one failed, or a clash
  // stands. One write for the many changes of a drag.
  s.note ??= setTimeout(() => {
    s.note = undefined;
    keep(s);
  }, 1000);
  tell();
}

// The teacher's two answers to a clash. The other version: the saver starts over from the server's sheet, and the
// kept change is dropped. This one: it is saved over what the server holds now.
// The other version's answer counts only while the clash stands: one that comes after the teacher chose this one
// instead would put the old sheet in place of what was just saved.
export function reset(sheet: Sheet) {
  if (!savers.get(sheet.id)?.clash) return;
  forget(sheet.id);
  return open(sheet);
}
// The server's sheet is what is saved now, so what the editor shows is unsaved, also where it is back at what was
// saved before, and goes. Where the server cannot be asked the clash stands, for another try. Says what
// `refused` says where the server gave no sheet.
export async function overwrite(id: number) {
  const s = savers.get(id);
  const sheet = s && (await ask<Sheet>(`/sheets/${id}`).catch((e: Refusal) => e));
  if (sheet instanceof Error) return refused(id, sheet);
  if (!s || !sheet || s.dead || !s.clash) return;
  s.base = sheet.version;
  s.saved = { doc: read(sheet.doc), title: sheet.title };
  s.clash = false;
  send(s);
  tell();
}
// What a clash's choice was answered with, where the server gave no sheet. A 404 says that the sheet is gone only
// where it was served for the saver's owner: then the clash is over, for there is no other version, and the change
// is kept as that of any sheet deleted elsewhere. Under another account's session, or with the session gone: the
// road of a save that finds it so. The login shows, the change is kept for its owner, and the clash stands again
// after the owner's login. Anything else is "failed", also a 404 that names nobody: the banner stays for another
// try.
export function refused(id: number, e: Refusal) {
  const s = savers.get(id);
  if (!s || s.dead) return;
  if (e.by === s.owner) {
    s.gone = true;
    s.clash = false;
    s.lost = [];
    keep(s);
    return tell(1);
  }
  if (e.message !== "401" && e.by === undefined) return "failed" as const;
  s.stop = true;
  tell();
  signedOut();
}
// Tells the other tabs what this one took of a sheet deleted elsewhere: the set fires their storage event, the removal
// after it leaves no trace in the store.
function announce(id: number, took: Kept, to: number | null) {
  try {
    // Kept for good, so a tab that opens later hears the choice too. Written before the event.
    localStorage.setItem(`took:${id}`, JSON.stringify({ to, print: print(took) }));
    localStorage.setItem(`ended:${id}`, JSON.stringify({ doc: took.doc, title: took.title, to }));
    localStorage.removeItem(`ended:${id}`);
  } catch {
    // The store is full or shut: the other tabs keep their choice.
  }
}
// Tells the other tabs that a save of this sheet landed: their set fires the storage event, the removal leaves no trace.
function announceSaved(id: number, version: number) {
  try {
    localStorage.setItem(`saved:${id}`, String(version));
    localStorage.removeItem(`saved:${id}`);
  } catch {
    // The store is full or shut: the other tabs keep what they show.
  }
}
// The editor of a sheet is told that a newer version was saved in another tab (#720).
const fresh = new Map<number, () => void>();
export function onNewer(id: number, told: () => void) {
  fresh.set(id, told);
  return () => void fresh.delete(id);
}
// A window with no change of its own learns of a newer version saved elsewhere, and the editor loads it (#720). Gives
// the sheet to show, or nothing where there is none newer, or where a change was made here meanwhile: `last` is what
// the editor holds now, so a key typed while the server was asked keeps the window as it is.
export async function newer(id: number, last: () => Kept) {
  const s = savers.get(id);
  if (!s || unsaved(s)) return;
  // A 404 that the saver's owner gets: the sheet is deleted elsewhere, and the change is kept as such.
  const sheet = await ask<Sheet>(`/sheets/${id}`).catch((e: Refusal) => (e.message === "404" && e.by === s.owner ? e : undefined));
  if (sheet instanceof Error) {
    refused(id, sheet);
    // Another tab may have taken its choice already: that choice is applied here too, as after a save.
    const heard = s.gone && heardOf(s.id);
    if (heard && !s.dead && s.choice !== "busy") endWith(s, heard);
    return;
  }
  const now = last();
  if (!sheet || savers.get(id) !== s || s.dead || unsaved(s) || now.doc !== s.want.doc || now.title !== s.want.title || sheet.version <= s.base) return;
  return open(sheet);
}
// The editor of a sheet whose choice another tab ended is told where to go: to the new sheet, or the list.
const ends = new Map<number, (to: number | null) => void>();
export function onEnded(id: number, told: (to: number | null) => void) {
  ends.set(id, told);
  return () => void ends.delete(id);
}
// A short fingerprint of a sheet's work, to tell whether two tabs hold the same change (cyrb53, #718).
function print(k: Kept): string {
  const text = JSON.stringify({ doc: k.doc, title: k.title });
  let h1 = 0xdeadbeef;
  let h2 = 0x41c6ce57;
  for (let i = 0; i < text.length; i++) {
    const c = text.charCodeAt(i);
    h1 = Math.imul(h1 ^ c, 2654435761);
    h2 = Math.imul(h2 ^ c, 1597334677);
  }
  h1 = Math.imul(h1 ^ (h1 >>> 16), 2246822507) ^ Math.imul(h2 ^ (h2 >>> 13), 3266489909);
  h2 = Math.imul(h2 ^ (h2 >>> 16), 2246822507) ^ Math.imul(h1 ^ (h1 >>> 13), 3266489909);
  return String(4294967296 * (2097151 & h2) + (h1 >>> 0));
}
// The choice another tab took for a sheet deleted elsewhere, as the store keeps it (#718).
function heardOf(id: number): { to: number | null; print: string } | null {
  try {
    return JSON.parse(localStorage.getItem(`took:${id}`) ?? "null");
  } catch {
    return null;
  }
}
// The records of sheets whose choice was handed over by this tab, for the tab's open to take up (#718).
const handed = new Map<number, Record>();
// Another tab took the sheet deleted elsewhere. Where it holds the same work its choice ends, and where it holds other
// work its change is written back, so the removal of the other tab's record leaves no loss.
addEventListener("storage", (e) => {
  // Another tab took a sheet's record out: a tab that still holds unsaved work of it writes its own back. That tab's
  // removal may reach the store after this tab's own write, which then would be gone with it.
  const out = /^unsaved:(\d+)$/.exec(e.key ?? "");
  if (out && e.newValue === null) {
    const s = savers.get(Number(out[1]));
    if (s && !s.dead && unsaved(s)) keep(s);
    return;
  }
  const saved = /^saved:(\d+)$/.exec(e.key ?? "");
  if (saved) {
    if (e.newValue !== null) fresh.get(Number(saved[1]))?.();
    return;
  }
  const m = /^ended:(\d+)$/.exec(e.key ?? "");
  if (!m || e.newValue === null) return;
  const id = Number(m[1]);
  const s = savers.get(id);
  const heard = heardOf(id);
  if (!s || !s.gone || s.dead || s.choice === "busy" || !heard) return;
  endWith(s, heard);
});
// Where another tab's choice holds the same work as this saver, this one ends and the editor goes where that tab went.
// Where it holds other work, the change is kept.
function endWith(s: Saver, heard: { to: number | null; print: string }) {
  if (print({ doc: s.want.doc, title: s.want.title }) === heard.print) {
    // The other tab's sheet holds this work: the record goes too, or the next start would ask again.
    forget(s.id);
    ends.get(s.id)?.(heard.to);
  } else {
    keep(s);
    tell();
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
// A sheet deleted elsewhere is kept as a new one, with the title and the page as they stand at the press. Gives the
// new sheet, and the old saver and its record go. Where the server made none this gives "failed", and the choice
// stands with all that was kept: after a failure the saver says so, and a session that ran out brings the login.
// While one is under way a second press does nothing: there is one new sheet. Another account's session, which a
// login in another tab brought, gets no sheet of this teacher: the login shows, as for a save that finds it so.
export async function keepAsNew(id: number) {
  const s = savers.get(id);
  if (!s || s.dead || !s.gone || s.choice === "busy") return;
  s.choice = "busy";
  s.choiceProblems = undefined;
  tell();
  const want = s.want;
  const body = JSON.stringify({ title: want.title.trim() || "Unbenanntes Blatt", doc: want.doc });
  try {
    const who = await ask<{ id: number }>("/me");
    if (who.id !== s.owner) {
      signedOut();
      throw new Error("401");
    }
    // Another tab kept the sheet first: its new sheet is found, not made again. Where this tab holds other work, that work
    // goes to that sheet as a clash.
    const heard = heardOf(id);
    let there: Sheet | undefined;
    // A saver of that sheet in this tab would not take the change up: then a sheet is made, and nothing is lost.
    if (typeof heard?.to === "number" && !savers.has(heard.to)) {
      try {
        there = await ask<Sheet>(`/sheets/${heard.to}`);
      } catch (e) {
        const { message, by } = e as Refusal;
        // Another account's 404 says nothing of the sheet: the login shows, as for the check above.
        if (message === "404" && by !== undefined && by !== s.owner) {
          signedOut();
          throw new Error("401");
        }
        // Only a 404 served for the owner says that sheet is not there: any other failure ends the press.
        if (message !== "404" || by !== s.owner) throw e;
      }
    }
    if (heard && there) {
      // Where this tab holds other work, it goes to that sheet as a clash, through the record `open` takes up. The
      // store has it too, for a reload before that open.
      if (!s.dead && print({ doc: s.want.doc, title: s.want.title }) !== heard.print) {
        const record: Record = { owner: s.owner, base: 0, doc: s.want.doc, title: s.want.title, name: there.title, lists: true };
        handed.set(there.id, record);
        try {
          localStorage.setItem(key(there.id), JSON.stringify(record));
        } catch {
          // The store is full or shut: the change lives on in this window alone.
        }
      }
      forget(id);
      return there;
    }
    // A press before this one sent a sheet whose answer never came: the server may hold it, so it is found, not made again.
    const prior = s.asked;
    const found = prior && (await ask<Sheet[]>("/sheets")).find((x) => x.title === (prior.title.trim() || "Unbenanntes Blatt") && same(x.doc, prior.doc));
    if (!found) {
      s.asked = want;
      keep(s);
    }
    const sheet = found || (await ask<Sheet>("/sheets", { method: "POST", headers: { "Content-Type": "application/json" }, body }));
    // What the new sheet holds: the change asked for, which the found sheet holds too.
    const took = found && prior ? prior : want;
    // A change made while the server was asked goes along: the new sheet's saver finds it kept, and sends it.
    if (!s.dead && (!same(s.want.doc, took.doc) || s.want.title !== took.title)) {
      const record: Record = { owner: s.owner, base: sheet.version, doc: s.want.doc, title: s.want.title, name: sheet.title };
      try {
        localStorage.setItem(key(sheet.id), JSON.stringify(record));
      } catch {
        // The store is full or shut: that change is lost with the old sheet.
      }
    }
    announce(id, took, sheet.id);
    forget(id);
    return sheet;
  } catch (e) {
    // The login shows, or somebody signed in meanwhile: no word on the connection then.
    s.choice = ["401", "stale"].includes((e as Error).message) ? undefined : "failed";
    s.choiceProblems = (e as Refusal).problems;
    if (!s.dead) tell();
    return "failed" as const;
  }
}
// The other answer: what was kept of a sheet deleted elsewhere is dropped, and this says true then. It is the only
// copy, so the teacher is asked once more, and only the owner's own session may drop it: with the session gone or
// another account's the login shows and all stays, as for `keepAsNew`. Where the server cannot say who is signed
// in, the saver says so and the choice stands.
export async function discard(id: number) {
  const s = savers.get(id);
  if (!s || s.dead || !s.gone || s.choice === "busy") return false;
  if (!confirm(`Was von „${s.want.title}“ noch da ist, endgültig verwerfen?`)) return false;
  s.choice = "busy";
  tell();
  try {
    const who = await ask<{ id: number }>("/me");
    if (who.id !== s.owner) {
      signedOut();
      throw new Error("401");
    }
    if (s.dead) return false;
    announce(id, s.want, null);
    forget(id);
    return true;
  } catch (e) {
    s.choice = ["401", "stale"].includes((e as Error).message) ? undefined : "failed";
    if (!s.dead) tell();
    return false;
  }
}

// Waits for the save under way, which may hold an older document, then sends what is unsaved and waits for that:
// until it landed, failed, or was given up after 20 s. A save that fails is not waited for again.
// True when the server holds the document the editor had at the call, once the waits are over. The title does not count:
// the server names the file, and the document is what prints.
export async function flush(id: number) {
  const s = savers.get(id);
  if (!s) return true;
  const asked = s.want;
  const idle = () => s.out && new Promise<void>((done) => s.idle.push(done));
  const failed = s.tries;
  await idle();
  if (s.tries > failed) return false;
  send(s);
  const went = s.out;
  await idle();
  // The server holds the doc of the press, or a newer one this flush sent.
  return same(s.saved.doc, asked.doc) || (!!went && s.saved === went);
}

// The account is known: at the app's start, a login or a logout. Another account's savers leave this window, their
// changes kept in the browser's store for their owner; this account's go on where the session had run out. And each
// change the store keeps for this account, of a sheet with no saver here, is taken up without waiting for its sheet
// to be opened: the sheet is asked for and its saver sends at once, or shows the clash as a notice. The editor may
// ask for the same sheet meanwhile: whoever comes second finds the saver and goes on with it. A sheet its owner no
// longer has was deleted elsewhere: its record stays, and a saver made from it holds the change until the teacher
// has chosen. Only where the 404 was served for the owner, for another account may have signed in in another tab
// since `owner` was heard, and that one's 404 says nothing. Any other failure leaves the record for the next
// start.
export function enter(owner?: number) {
  me = owner;
  countLogin();
  let ids: number[] = [];
  try {
    ids = Object.keys(localStorage).flatMap((k) => (k.startsWith("unsaved:") ? [Number(k.slice(8))] : []));
  } catch {
    // The store is shut: nothing was kept.
  }
  const mine = (id: number) => me === owner && !savers.has(id) && kept(id)?.owner === owner;
  for (const id of ids.filter(mine)) {
    ask<Sheet>(`/sheets/${id}`).then(
      (sheet) => mine(id) && open(sheet),
      (e: Refusal) => {
        const record = e.message === "404" && e.by === owner && mine(id) && kept(id);
        if (!record || owner === undefined) return;
        const saved = { doc: record.doc, title: record.name ?? record.title ?? "Unbenanntes Blatt" };
        const want = { doc: read(record.doc), title: record.title ?? saved.title };
        const asked = record.asked && { doc: read(record.asked.doc), title: record.asked.title };
        const s: Saver = { id, owner, base: record.base, saved, want, asked, lost: [], tries: 0, clash: false, stop: false, gone: true, dead: false, open: false, kept: true, late: false, idle: [] };
        savers.set(id, s);
        tell(1);
        // Another tab may have chosen for it already (#718).
        const heard = heardOf(id);
        if (heard) endWith(s, heard);
      },
    );
  }
  for (const s of savers.values()) {
    if (s.owner === owner) {
      s.stop = false;
      send(s);
    } else {
      keep(s);
      kill(s);
    }
  }
  tell();
}

// A window that shuts runs no script after this: the change is kept, and sent only where no save is under way, for
// two saves of one sheet on one version would clash with each other. One the browser already dropped still counts:
// it may arrive after the tab is gone (#390).
addEventListener("pagehide", () =>
  savers.forEach((s) => {
    send(s, true);
    keep(s);
  }),
);
document.addEventListener("visibilitychange", () => document.hidden && savers.forEach(keep));
addEventListener("online", () => savers.forEach((s) => s.tries && send(s)));
// The browser asks before the window shuts while a change is unsaved.
addEventListener("beforeunload", (e) => {
  if (![...savers.values()].some(unsaved)) return;
  e.preventDefault();
  e.returnValue = true;
});
