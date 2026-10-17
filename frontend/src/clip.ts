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

// Empties the clipboard of the editor's copy. Where this page made it, at once, in the click that allows it: what
// was copied in another app since goes too. After a reload the page knows the copy only by reading the clipboard,
// which it does where it may without asking.
export async function wipe() {
  if (ours) {
    ours = false;
    return navigator.clipboard?.writeText("").catch(() => {});
  }
  const mark = localStorage.getItem("copied");
  if (!mark) return;
  try {
    const leave = await navigator.permissions.query({ name: "clipboard-read" as PermissionName });
    if (leave.state === "granted" && hash((await navigator.clipboard.readText()).replace(/\r\n/g, "\n")) === mark) await navigator.clipboard.writeText("");
  } catch {
    // A browser that cannot tell leaves the clipboard as it is.
  }
}
