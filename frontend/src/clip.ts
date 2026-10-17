// The editor's last copy on the system's clipboard: its words and its picture. A logout takes them off again, so
// the next one at a shared computer finds no picture of the sheets there, if nothing was copied since.

// A mark of the copied words, apart from the blocks: a logout takes the blocks away, and the words still lie on
// the system's clipboard, where the next account must not get them as a text. The mark gives no word away.
export const hash = (words: string) => String([...words].reduce((h, c) => (h * 33) ^ c.codePointAt(0)!, 5381) >>> 0);

// Whether the clipboard still holds the editor's copy, as far as this page knows: a copy in another app takes the
// focus from the window first, and one in a field comes here as a copy too. The editor's own sets it after its copy.
let ours = false;
export const copied = () => (ours = true);
addEventListener("blur", () => (ours = false));
addEventListener("copy", () => (ours = false), true);

// Empties the clipboard if it still holds the editor's copy. After a reload the page knows it only by reading the
// clipboard, which it does where it may without asking.
export async function wipe() {
  let still = ours;
  ours = false;
  const mark = localStorage.getItem("copied");
  if (!still && mark) {
    try {
      const leave = await navigator.permissions.query({ name: "clipboard-read" as PermissionName });
      still = leave.state === "granted" && hash((await navigator.clipboard.readText()).replace(/\r\n/g, "\n")) === mark;
    } catch {
      // A browser that cannot tell leaves the clipboard as it is.
    }
  }
  if (still) await navigator.clipboard?.writeText("").catch(() => {});
}
