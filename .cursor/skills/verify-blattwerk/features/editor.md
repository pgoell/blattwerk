# Editor

The editor is the sheet a teacher writes on after signing up and creating a sheet. A text block takes words, and those words are still there after a reload.

## Sub-features

- `editor-open` signs up from an invite link and opens a new sheet.
- `editor-type` inserts a text, writes `Hallo`, and leaves the field.
- `editor-persist` shows the same word after a reload and in the stored sheet.

## How to get to it (user POV)

- Open `/einladung/<token>` from `python -m blattwerk invite --admin`, fill E-Mail and Passwort, press `Konto anlegen`.
- On `Meine Blätter`, press `Neues Blatt`.
- In the toolbar `Einfügen`, press `Text`.
- Type, then press `F2` to leave the field. A double-click opens the field again. The first visit also offers `Beenden` on the Rundgang.

## Driving it with drive.py

Preconditions:

- `drive.py launch` has printed an origin and `drive.py doctor` has printed `doctor ok`.
- No account in this data directory has used the invite this drive is about to create. The script creates the invite itself.
- Chromium can launch headless. The script grants clipboard-read and clipboard-write.

- **Sign up.** The script opens the invite, fills `verify-<run-id>-editor@example.com` and `verify-blatt`, and presses `Konto anlegen`. The heading `Meine Blätter` is visible.
- **New sheet.** Press `Neues Blatt`. `main.editor[data-ready="1"]` is visible, the textbox `Titel` reads `Unbenanntes Blatt`, and fonts and the desk measure have settled.
- **Leave the tour.** If `section.tour` is visible, press `Beenden`. The tour section is gone. `result.txt` records `tour Beenden` or `tour no tour`.
- **Insert and type.** Press `Text` in the toolbar `Einfügen`. The selected block's `.ProseMirror` is focused. Type `Hallo`. Press `F2`. The field is gone and one `.block.sel` remains.
- **Save and reload.** The header status matches `Speichert` and then reads `Gespeichert`. Reload. The sheet block's text is `Hallo`.
- **Stored sheet.** `GET /api/sheets/<id>` returns one block whose `props.text` is `Hallo`.
- **Proof.** `editor/before-reload.png`, `editor/after-reload.png`, the matching `.aria.txt` files, `editor/sheet.json`, and `editor/result.txt`.

The command for this feature alone, after launch and doctor:

```sh
uv run python .cursor/skills/verify-blattwerk/drive.py drive editor
```

## Gotchas

- The browser origin is `http://localhost`. On `http://127.0.0.1` the `Secure` session cookie is not kept, signup looks successful, and the next request is the login page.
- The Rundgang opens the first time this browser profile visits the editor. Tests set `localStorage.tour` so it stays shut. This drive presses `Beenden` instead.
- `F2` and `Escape` leave the text field (`frontend/src/pages/Field.tsx`). `Control+C` while the field is focused copies the field's words, not the block.
- A teacher's save waits 2 seconds (`saveAfter` in `frontend/src/saves.ts`). The header reads `Gespeichert` when nothing is dirty. Wait until it has shown `Speichert` and then `Gespeichert` before reload, or the reload races the save.
- After reload the block is not selected. The proof is the word on the sheet, not an enabled Kopieren button.
- A viewport under 1024 px, or a theme other than Blattform, moves `Text` to the dock. The dock is still `role=toolbar` named `Einfügen`. This drive's viewport is 1400×1000 and the default theme. A narrow window was not driven.
- Do not reload with `page.reload()` inside `expect_response` and `.finished()`. That hangs when it catches a response from the old page.
