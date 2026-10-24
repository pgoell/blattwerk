import { forget, keep, savers, tell, unsaved, type Kept, type Record, type Saver } from "./model";

// Tells the other tabs what this one took of a sheet deleted elsewhere: the set fires their storage event, the removal
// after it leaves no trace in the store.
export function announce(id: number, took: Kept, to: number | null) {
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
export function announceSaved(id: number, version: number) {
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
// The editor of a sheet whose choice another tab ended is told where to go: to the new sheet, or the list.
const ends = new Map<number, (to: number | null) => void>();
export function onEnded(id: number, told: (to: number | null) => void) {
  ends.set(id, told);
  return () => void ends.delete(id);
}
// A short fingerprint of a sheet's work, to tell whether two tabs hold the same change (cyrb53, #718).
export function print(k: Kept): string {
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
export function heardOf(id: number): { to: number | null; print: string } | null {
  try {
    return JSON.parse(localStorage.getItem(`took:${id}`) ?? "null");
  } catch {
    return null;
  }
}
// The records of sheets whose choice was handed over by this tab, for the tab's open to take up (#718).
export const handed = new Map<number, Record>();
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
export function endWith(s: Saver, heard: { to: number | null; print: string }) {
  if (print({ doc: s.want.doc, title: s.want.title }) === heard.print) {
    // The other tab's sheet holds this work: the record goes too, or the next start would ask again.
    forget(s.id);
    ends.get(s.id)?.(heard.to);
  } else {
    keep(s);
    tell();
  }
}
