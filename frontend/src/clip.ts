// The editor's last copy on the system's clipboard: its words and its picture. A logout takes them off again, so
// the next one at a shared computer finds no picture of the sheets there.

// A mark of the copied words, apart from the blocks: a logout takes the blocks away, and the words still lie on
// the system's clipboard, where the next account must not get them as a text. The mark gives no word away.
export const hash = (words: string) => String([...words].reduce((h, c) => (h * 33) ^ c.codePointAt(0)!, 5381) >>> 0);

// Whether this page put the last copy there: a copy in one of its fields comes here as a copy too, and is no longer
// the editor's. The editor's own sets it after its copy. A copy in another app since is not seen.
let ours = false;
export const copied = () => (ours = true);
addEventListener("copy", () => (ours = false), true);

// Who is signed in, set by the app: the copied words are only the account's whose blocks lie in the store.
let me: number | undefined;
export const signedIn = (id?: number) => (me = id);

// Words copied in an open text or a field of the sheet: a mark of them, whatever the whitespace, and whose account
// copied them. A logout keeps the mark and drops the owner, so the next account and this one again pastes none.
const TYPED = "typed-copy";
const norm = (words: string) => hash(words.replace(/\r\n/g, "\n").replace(/\s+/g, " ").trim());
const typed = (): { owner?: number; mark: string } | null => {
  try {
    return JSON.parse(localStorage.getItem(TYPED) ?? "null");
  } catch {
    return null;
  }
};
export function dropOwner() {
  const t = typed();
  if (t) localStorage.setItem(TYPED, JSON.stringify({ mark: t.mark }));
}
// Whether words are such a copy that another account, or none, made.
export function refused(words: string) {
  const t = typed();
  return !!t && words.trim() !== "" && t.mark === norm(words) && (t.owner === undefined || t.owner !== me);
}

// Marks the words of a copy or cut made on any page: what the browser put out, read after the page's own copy has
// run. Where none is read, the selection stands in for it.
export function mark(words: string) {
  // With no one signed in, as on the login page, the words are no account's.
  if (me === undefined) return;
  localStorage.setItem(TYPED, JSON.stringify({ owner: me, mark: norm(words) }));
  ours = true;
}
for (const kind of ["copy", "cut"]) {
  addEventListener(kind, (e) => {
    const el = e.target as HTMLTextAreaElement;
    let words = (e as ClipboardEvent).clipboardData?.getData("text/plain") ?? "";
    if (!words.trim()) {
      words =
        el.matches?.("textarea, input") && el.selectionStart !== null
          ? el.value.slice(el.selectionStart, el.selectionEnd ?? 0)
          : String(getSelection() ?? "");
    }
    if (words.trim()) mark(words);
  });
}

// Another account's copy, or one made before a logout, pastes into no field on any page. Caught on the way down,
// before the editor or a field takes it.
addEventListener(
  "paste",
  (e) => {
    const mark = localStorage.getItem("copied");
    if (refused(e.clipboardData?.getData("text/plain") ?? "")) {
      e.preventDefault();
      e.stopImmediatePropagation();
      return;
    }
    if (!mark || hash((e.clipboardData?.getData("text/plain") ?? "").replace(/\r\n/g, "\n")) !== mark) return;
    let owner: unknown;
    try {
      owner = JSON.parse(localStorage.getItem("clip") ?? "null")?.owner;
    } catch {
      // A broken store holds no account's copy.
    }
    if (me !== undefined && owner === me) return;
    e.preventDefault();
    e.stopImmediatePropagation();
  },
  true,
);

// Empties the clipboard of the editor's copy. Where this page made it, at once, in the click that allows it: what
// was copied in another app since goes too. After a reload the page knows the copy only by reading the clipboard,
// which it does where it may without asking.
export async function wipe() {
  if (ours) {
    ours = false;
    return navigator.clipboard
      ?.writeText("")
      .then(() => localStorage.removeItem(TYPED))
      .catch(() => {});
  }
  const mark = localStorage.getItem("copied");
  const words = typed()?.mark;
  if (!mark && !words) return;
  try {
    const leave = await navigator.permissions.query({ name: "clipboard-read" as PermissionName });
    if (leave.state !== "granted") return;
    const text = (await navigator.clipboard.readText()).replace(/\r\n/g, "\n");
    if (hash(text) === mark || (words && norm(text) === words)) await navigator.clipboard.writeText("");
    // The copy is gone or was never there: a later copy from another app must not be refused by this mark.
    localStorage.removeItem(TYPED);
  } catch {
    // A browser that cannot tell leaves the clipboard as it is.
  }
}
