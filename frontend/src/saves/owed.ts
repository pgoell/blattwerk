import { keep, savers, tell, type Owed } from "./model";

export type { Owed };

// A maths change the session ran out on: kept by the saver, red bar at once, redone by the editor after the login.
// `change` holds only what the click changed: the redo lays it over the block as it is then.
// The browser keeps the owed clicks under a key of their own, each with its teacher: every tab adds to the list
// there, so no tab's record of its document drops another tab's click (#890). Null where the store cannot be read.
const owedKey = (id: number) => `owed:${id}`;
export function owedIn(id: number): (Owed & { owner: number })[] | null {
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
// A later click carried these and landed, so each is on the sheet. Left owed, the redo would put the old change
// back over that answer (#908). `changes` are the objects `owe` stored: the sheet is the saver that still holds them.
export function dropOwed(block: string, changes: Owed["change"][]) {
  if (!changes.length) return;
  for (const s of savers.values()) {
    if (s.dead || !s.owed) continue;
    const hit = s.owed.filter((e) => e.block === block && changes.some((c) => c === e.change));
    if (!hit.length) continue;
    const left = s.owed.filter((e) => !hit.includes(e));
    s.owed = left.length ? left : undefined;
    const all = owedIn(s.id);
    if (all) {
      const mine = all.filter((e) => e.owner === s.owner);
      const rest = all.filter((e) => e.owner !== s.owner);
      for (const gone of hit) {
        const at = mine.findIndex((e) => e.block === block && JSON.stringify(e.change) === JSON.stringify(gone.change));
        if (at >= 0) mine.splice(at, 1);
      }
      owedTo(s.id, [...mine, ...rest]);
    }
    keep(s);
    tell();
  }
}
