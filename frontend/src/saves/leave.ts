import { countLogin, showLogin as signedOut, type Refusal } from "../api";
import { read, type Sheet } from "../sheet";
import { forget, keep, kept, key, kill, me, same, savers, setAccount, tell, type Kept, type Record, type Saver } from "./model";
import { ask, open, send } from "./sync";
import { announce, endWith, handed, heardOf, print } from "./tabs";

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
  setAccount(owner);
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
