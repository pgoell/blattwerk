import { api, showLogin as signedOut, signed, type Refusal } from "../api";
import { read, type Doc, type Sheet } from "../sheet";
import { AFTER, keep, kept, kill, refusal, same, savers, served, tell, unsaved, waits, type Kept, type Saver } from "./model";
import { owedIn } from "./owed";
import { announceSaved, endWith, handed, heardOf } from "./tabs";

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

export function plan(s: Saver, ms: number) {
  clearTimeout(s.timer);
  s.timer = setTimeout(() => send(s), ms);
}

// An HTTP status, or a 401 from a session that has since changed. Anything else is the browser dropping the fetch.
const answered = (e: Refusal) => /^\d+$/.test(e.message) || e.message === "stale";

// One save of a sheet at a time, always based on the saver's version. `closing` is the window that shuts.
export function send(s: Saver, closing = false) {
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
