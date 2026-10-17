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

// Whether the store holds a mark of a copy made by another account than `id`, or by none it knows: the login of `id`
// takes that copy off the system's clipboard.
export function othersCopy(id: number) {
  const t = typed();
  if (t && t.owner !== id) return true;
  if (!localStorage.getItem("copied")) return false;
  let owner: unknown;
  try {
    owner = JSON.parse(localStorage.getItem("clip") ?? "null")?.owner;
  } catch {
    // A broken store holds no account's copy.
  }
  return owner !== id;
}

// The login's own wipe, begun in its click, as Safari lets only a write begun there through: the write waits for the
// answer, empties the clipboard when it names another account than the copy's, and with the same account writes
// nothing. The wipe in `enter` comes after it for a browser without such a write.
export function wipeAt(login: Promise<{ id: number }>) {
  const clipboard = navigator.clipboard;
  if (!clipboard?.write || typeof ClipboardItem === "undefined" || (!localStorage.getItem("copied") && !typed())) return;
  const empty = login.then((to) => (othersCopy(to.id) ? new Blob([""], { type: "text/plain" }) : Promise.reject(new Error("own copy"))));
  // A failed login rejects it too; that is no fault.
  empty.catch(() => {});
  clipboard.write([new ClipboardItem({ "text/plain": empty })]).catch(() => {});
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

// Empties the clipboard of the editor's copy, at once, in the click that allows it: wherever a mark of one is stored,
// made by this page or by one before a reload. It reads nothing and asks for nothing, so what was copied in another
// app since goes too (#763). The marks go with the copy; a refused write keeps them, and the paste stays refused.
export function wipe() {
  const clipboard = navigator.clipboard;
  if (!clipboard || (!ours && !localStorage.getItem("copied") && !typed())) return;
  ours = false;
  const late = writes.size ? Promise.all(writes) : undefined;
  const done = clipboard.writeText("");
  // A copy's write still on its way lands after this one and puts the copy back: empty it again then, and keep the
  // marks till that is done.
  done
    .then(() => late?.then(() => clipboard.writeText("")))
    .then(() => (localStorage.removeItem(TYPED), localStorage.removeItem("copied")))
    .catch(() => {});
  return done.catch(() => {});
}

// The editor's copies still on their way to the clipboard, for the wipe.
const writes = new Set<Promise<unknown>>();
export function onTheWay(write: Promise<unknown>) {
  writes.add(write);
  write.finally(() => writes.delete(write));
}
