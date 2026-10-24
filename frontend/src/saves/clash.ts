import { showLogin as signedOut, type Refusal } from "../api";
import { read, type Sheet } from "../sheet";
import { AFTER, forget, keep, savers, tell, unsaved, type Kept, type Saver } from "./model";
import { ask, open, plan, send } from "./sync";
import { endWith, heardOf } from "./tabs";


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
