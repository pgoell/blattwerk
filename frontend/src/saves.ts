import { useSyncExternalStore } from "react";
import { api, type User } from "./api";
import { read, type Doc, type Sheet } from "./sheet";

// Each sheet has one saver, and it outlives the editor: a save that is out, fails or never answers when the teacher
// has left the sheet is still seen through, and no load waits for it. The editor says what the sheet holds now and
// reads from here whether that is saved.
type Kept = { doc: Doc; title: string };
type Saver = {
  id: number;
  owner: number;
  // The last version the server confirmed: every save is based on it.
  base: number;
  // What the server is known to hold, and the newest the editor has.
  saved: Kept;
  want: Kept;
  // What is on the wire, and what went with no answer since the server last confirmed a version: it may hold one of
  // those. The first and the newest are kept: the first that arrived is the one it took.
  out?: Kept;
  lost: Kept[];
  tries: number;
  // The server holds another device's document: saving stops until the teacher has chosen.
  clash: boolean;
  // The session ran out: nothing goes until a login or the next visit.
  stop: boolean;
  // The sheet was deleted.
  gone: boolean;
  // Another account took over: nothing of this one is sent or heard any more.
  dead: boolean;
  // Whether the sheet's editor is there.
  open: boolean;
  // Whether a record of this saver lies in the browser's store.
  kept: boolean;
  // Unsaved for over a second.
  late: boolean;
  timer?: number;
  slow?: number;
  idle: (() => void)[];
};
// What the browser keeps of an unsaved change, for the next visit. `title` only where it changed here, `sent` only
// where a document other than `doc` is on the wire or went without an answer: the server may hold any of them.
type Record = { owner: number; base: number; doc: Doc; title?: string; sent?: Doc[] };
export type Save = { id: number; owner: number; title: string; saved: Kept; unsaved: boolean; failed: boolean; stopped: boolean; clash: boolean; late: boolean };

const savers = new Map<number, Saver>();
// Who is signed in, as the app said last, and what the app does when a save finds the session gone.
let me: number | undefined;
let signedOut = () => {};
export const onSignedOut = (then: () => void) => void (signedOut = then);
const heard = new Set<() => void>();
// `landed` counts the saves the server took: the list asks anew at each.
let shot = { list: [] as Save[], landed: 0 };
const key = (id: number) => `unsaved:${id}`;
const same = (a: Doc, b: Doc) => JSON.stringify(a) === JSON.stringify(b);
// A save that got no answer counts too: the server may hold it though the teacher has undone it since.
const unsaved = (s: Saver) => !s.gone && (!!s.out || s.lost.length > 0 || s.want.doc !== s.saved.doc || s.want.title !== s.saved.title);

// Tells who reads the savers, where what they read has changed: the editor draws anew only then.
function tell(landed = 0) {
  const list = [...savers.values()].map((s) => ({ id: s.id, owner: s.owner, title: s.want.title, saved: s.saved, unsaved: unsaved(s), failed: s.tries > 0 || s.stop || s.gone, stopped: s.stop, clash: s.clash, late: s.late }));
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
      const record: Record = { owner: s.owner, base: s.base, doc: s.want.doc, title: s.want.title === s.saved.title ? undefined : s.want.title, sent: sent.length ? sent : undefined };
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
function ask<T>(path: string, init?: RequestInit) {
  const stop = new AbortController();
  const limit = setTimeout(() => stop.abort(), 20000);
  return api<T>(path, { ...init, signal: stop.signal }).finally(() => clearTimeout(limit));
}

function plan(s: Saver, ms: number) {
  clearTimeout(s.timer);
  s.timer = setTimeout(() => send(s), ms);
}

// One save of a sheet at a time, always based on the saver's version. `closing` is the window that shuts.
function send(s: Saver, closing = false) {
  clearTimeout(s.timer);
  if (s.dead || s.out || s.clash || s.stop || !unsaved(s)) return;
  const now = (s.out = s.want);
  // The title goes along only when it changed here, so a rename from the list stays.
  const named = now.title === s.saved.title ? {} : { title: now.title.trim() || "Unbenanntes Blatt" };
  const body = JSON.stringify({ doc: now.doc, version: s.base, ...named });
  // `keepalive` lets a save outlive the window. The browser sends no such request over 64 KiB, so a larger sheet
  // goes without it: left for another page of the app, it arrives all the same.
  const keepalive = (closing || !s.open) && new Blob([body]).size < 60 * 1024;
  s.slow ??= setTimeout(() => {
    s.late = true;
    tell();
  }, 1000);
  keep(s);
  tell();
  ask<Sheet>(`/sheets/${s.id}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body, keepalive }).then(
    (sheet) => {
      if (s.dead) return;
      s.base = sheet.version;
      s.saved = now;
      s.lost = [];
      s.tries = 0;
      settle(s, 1);
    },
    (e: Error) => fail(s, now, e.message),
  );
}

async function fail(s: Saver, now: Kept, status: string) {
  if (s.dead) return;
  if (status === "409") {
    // The server holds a newer version. It may be this browser's own save, whose answer never came: then it holds
    // a document sent from here, and saving goes on from its version.
    const sheet = await ask<Sheet>(`/sheets/${s.id}`).catch((e: Error) => e.message);
    if (s.dead) return;
    if (typeof sheet !== "string") {
      const ours = [now, ...s.lost].find((k) => same(k.doc, sheet.doc));
      if (ours) {
        s.base = sheet.version;
        s.saved = ours;
        s.tries = 0;
      } else s.clash = true;
      s.lost = [];
      return settle(s, ours ? 1 : 0);
    }
    status = sheet;
  } else if (status !== "401" && status !== "404" && !s.lost.includes(now)) s.lost = [...s.lost.slice(0, 1), now];
  // Another account's sheet is as missing as a deleted one: only the owner's 404 means the sheet is gone. Who is
  // signed in now: 0 for nobody, nothing where that got no answer either.
  const who = status === "404" ? await ask<User>("/me").then((user) => user.id, (e: Error) => (e.message === "401" ? 0 : undefined)) : undefined;
  if (who === s.owner) {
    s.gone = true;
    s.lost = [];
    if (!s.open) savers.delete(s.id);
  } else if (status === "401" || who !== undefined) s.stop = true;
  else s.tries++;
  if (s.dead) return;
  settle(s);
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
  if (!unsaved(s) || s.clash || s.stop) return;
  if (s.tries) plan(s, Math.min(2000 * 2 ** (s.tries - 1), 30000));
  else if (s.open) plan(s, 2000);
  else send(s);
}

// The sheet as the editor shows it, given the server's answer. A saver with an unsaved change, or one ahead of this
// answer, goes on as it is: the sheet opened again before its save landed shows the change, and the next save is
// based on what that one brings. Else the saver starts from the answer, and a change the browser kept for this
// account comes back: as an unsaved one where the server still holds what it was based on or a save from here, and
// as a clash where the sheet was changed elsewhere meanwhile.
export function open(sheet: Sheet, owner: number): Sheet {
  let s = savers.get(sheet.id);
  if (!s || s.owner !== owner || !(unsaved(s) || s.base > sheet.version)) {
    if (s) s.dead = true;
    // `read` brings an old document up to date; that is no change.
    const saved = { doc: read(sheet.doc), title: sheet.title };
    s = { id: sheet.id, owner, base: sheet.version, saved, want: saved, lost: [], tries: 0, clash: false, stop: false, gone: false, dead: false, open: false, kept: false, late: false, idle: [] };
    savers.set(s.id, s);
    const record = kept(s.id);
    if (record?.owner === owner) {
      const ours = sheet.version > record.base && (record.sent?.some((doc) => same(doc, sheet.doc)) || same(record.doc, sheet.doc));
      const title = record.title ?? sheet.title;
      if (!same(record.doc, sheet.doc) || title !== sheet.title) s.want = { doc: read(record.doc), title };
      s.clash = unsaved(s) && sheet.version !== record.base && !ours;
      s.kept = true;
      keep(s);
    }
  }
  s.stop = false;
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
  return () => {
    if (s.dead) return;
    const want = last();
    s.want = s.want.doc === want.doc && s.want.title === want.title ? s.want : want;
    s.open = false;
    if (s.gone) savers.delete(id);
    keep(s);
    send(s);
    tell();
  };
}
// The editor says what the sheet holds after each change.
export function set(id: number, want: Kept) {
  const s = savers.get(id);
  if (!s || (s.want.doc === want.doc && s.want.title === want.title)) return;
  s.want = want;
  // A save that failed has a clock of its own. An undo back to what is saved leaves nothing to keep.
  if (!s.tries) plan(s, 2000);
  if (!unsaved(s)) keep(s);
  tell();
}

// The teacher's two answers to a clash. The other version: the saver starts over from the server's sheet, and the
// kept change is dropped. This one: it is saved over what the server holds now.
export function reset(sheet: Sheet, owner: number) {
  const s = savers.get(sheet.id);
  if (s) {
    s.dead = true;
    clearTimeout(s.timer);
    clearTimeout(s.slow);
    savers.delete(s.id);
    if (s.kept) localStorage.removeItem(key(s.id));
  }
  return open(sheet, owner);
}
export async function overwrite(id: number) {
  const s = savers.get(id);
  if (!s) return;
  s.base = (await ask<Sheet>(`/sheets/${id}`)).version;
  s.clash = false;
  send(s);
  tell();
}

// Waits for the save under way, which may hold an older document, then sends what is unsaved and waits for that:
// until it landed, failed, or was given up after 20 s. A save that fails is not waited for again.
export async function flush(id: number) {
  const s = savers.get(id);
  if (!s) return;
  const idle = () => s.out && new Promise<void>((done) => s.idle.push(done));
  const failed = s.tries;
  await idle();
  if (s.tries > failed) return;
  send(s);
  await idle();
}

// The account is known: at the app's start, a login or a logout. Another account's savers leave this window, their
// changes kept in the browser's store for their owner; this account's go on where the session had run out. And each
// change the store keeps for this account, of a sheet with no saver here, is taken up without waiting for its sheet
// to be opened: the sheet is asked for and its saver sends at once, or shows the clash as a notice. The editor may
// ask for the same sheet meanwhile: whoever comes second finds the saver and goes on with it. A sheet its owner no
// longer has takes its record along; any other failure leaves the record for the next start.
export function enter(owner?: number) {
  me = owner;
  let ids: number[] = [];
  try {
    ids = Object.keys(localStorage).flatMap((k) => (k.startsWith("unsaved:") ? [Number(k.slice(8))] : []));
  } catch {
    // The store is shut: nothing was kept.
  }
  const mine = (id: number) => me === owner && !savers.has(id) && kept(id)?.owner === owner;
  for (const id of ids.filter(mine)) {
    ask<Sheet>(`/sheets/${id}`).then(
      (sheet) => mine(id) && open(sheet, owner!),
      (e: Error) => e.message === "404" && mine(id) && localStorage.removeItem(key(id)),
    );
  }
  for (const s of savers.values()) {
    if (s.owner === owner) {
      s.stop = false;
      send(s);
    } else {
      keep(s);
      s.dead = true;
      clearTimeout(s.timer);
      clearTimeout(s.slow);
      savers.delete(s.id);
    }
  }
  tell();
}

// A window that shuts runs no script after this: the change is kept, and sent only where no save is under way, for
// two saves of one sheet on one version would clash with each other.
addEventListener("pagehide", () =>
  savers.forEach((s) => {
    send(s, true);
    keep(s);
  }),
);
document.addEventListener("visibilitychange", () => document.hidden && savers.forEach(keep));
addEventListener("online", () => savers.forEach((s) => s.tries && send(s)));
// The browser asks before the window shuts while a change is unsaved. Not for a download: that goes by an address
// too, and leaves the page where it is.
let stays = 0;
export function download(to: string) {
  stays = Date.now() + 1000;
  location.href = to;
}
addEventListener("beforeunload", (e) => {
  if (Date.now() < stays || ![...savers.values()].some(unsaved)) return;
  e.preventDefault();
  e.returnValue = true;
});
