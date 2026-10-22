# Paste and clipboard

Kopieren keeps the selected blocks. Einfügen, and Control+V, put a copy of those blocks on the sheet. The copies are still there after a reload.

## Sub-features

- `clip-buttons` copies the selected text with `Kopieren` and pastes it with `Einfügen`.
- `clip-keys` copies the selected paste with Control+C and pastes it with Control+V.
- `clip-persist` shows three `Hallo` blocks after a reload and in the stored sheet.

## How to get to it (user POV)

- Reach a selected text the way [Editor](./editor.md) describes, and leave the field with `F2` so the block, not the caret, has the keys.
- Press `Kopieren` and `Einfügen` in the header. On a narrow window they sit under `Mehr`.
- With the pasted block selected, press Control+C and Control+V. The buttons' shortcuts are the same keys.
- A cut is `Ausschneiden` or Control+X. A picture copied in another app is Einfügen of an image on the system clipboard. Those two entry points are not this drive.

## Driving it with drive.py

Preconditions:

- The editor preconditions hold: launched server, `doctor ok`, headless Chromium, clipboard permissions granted.
- The sheet's clipboard text has been cleared after the editor is ready (`navigator.clipboard.writeText('')`), so an older picture is not what Einfügen reads.

- **Type.** The same steps as the editor drive, through `F2`, with email `verify-<run-id>-clipboard@example.com`. One block is selected and its text is `Hallo`.
- **Buttons.** `Kopieren` is enabled. Press it, then `Einfügen`. `.block[data-id]` counts 2. `result.txt` records whether each button was in the header bar or under `Mehr`.
- **Keys.** The pasted block stays selected. Press Control+C, then Control+V. `.block[data-id]` counts 3.
- **Save and reload.** Header status goes through `Speichert` to `Gespeichert`. Reload. Three blocks read `Hallo`.
- **Stored sheet.** `GET /api/sheets/<id>` returns three blocks whose `props.text` is `Hallo`.
- **Proof.** `clipboard/before-reload.png`, `clipboard/after-reload.png`, the matching `.aria.txt` files (three paragraphs `Hallo`), `clipboard/sheet.json`, and `clipboard/result.txt`.

The command for this feature alone, after launch and doctor:

```sh
uv run python .cursor/skills/verify-blattwerk/drive.py drive clipboard
```

## Gotchas

- `Kopieren` is disabled when nothing is selected. `F2` leaves the block selected. A click on the empty corner of the sheet clears the selection (`unpick` in `tests/ui.py`).
- Einfügen of the editor's own copy uses the blocks in `localStorage` key `clip` when the clipboard words are that copy. A failure to read the clipboard still pastes those blocks (`pasteAny` in `frontend/src/pages/Editor.tsx`).
- Control+V is a paste event. The key handler does not paste on keydown (`Ctrl+V alone is not here` in the editor). Playwright's `Control+v` produces the paste the tests use.
- This drive does not paste a picture and does not cut. WebKit's Einfügen reads no picture the clipboard holds (`webkit_xfail` 204 in `tests/test_clipboard.py`). Do not treat a text paste as proof of that picture path.
- The pytest fixture clears the clipboard when an editor page opens, because one browser context shares a clipboard across tests. A second drive in one context without that clear can paste the previous picture.
- After reload the aria snapshot shows `Kopieren` disabled and three `Hallo` paragraphs. Disabled Kopieren is the empty selection, not a failed paste.
