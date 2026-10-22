---
name: verify-blattwerk
description: "Drive Blattomat (this repo, package blattwerk) the way a teacher does: sign up, open the editor, type, copy and paste, and run the WebKit browser tests. Use when a change needs proof on the real editor, the clipboard, or mise run test:webkit."
---

# Verify Blattwerk

Blattomat is the worksheet editor. The repo, the Python package and the commands are `blattwerk`. This skill drives a throwaway server and the built frontend. It does not touch `~/.local/share/blattwerk/` or the canary copy.

The harness is `.cursor/skills/verify-blattwerk/drive.py`. Run it from the repo root with `uv run python`. A one-shot that launches, drives the editor, drives paste and the clipboard, runs the two WebKit node ids below, tears the server down, and checks the proof files are still there:

```sh
uv run python .cursor/skills/verify-blattwerk/drive.py prove
```

`prove` exits 0 only when those three passes succeeded and the evidence survived cleanup. It does not run the rest of the WebKit suite, the native xvfb tests, or the PDF tests.

## Launch

The browser must open `http://localhost:<port>`. The session cookie is `Secure`. Chromium keeps that cookie on `localhost` and drops it on `http://127.0.0.1`, which is why `tests/ui.py` signs up over HTTPS and injects the cookie. Doctor checks `127.0.0.1` without a cookie. Do not point the browser at `127.0.0.1`.

```sh
uv run python .cursor/skills/verify-blattwerk/drive.py launch
```

That command:

- Refuses when `current.json` names a pid that is still running. Two drives of one server would share one account database. Run cleanup, or leave the other server alone.
- Picks a free port and a new directory under `/tmp/blattwerk-verify/data/<run-id>/`.
- Starts `uv run uvicorn blattwerk.app:app --host 127.0.0.1 --port <port>` with `BLATTWERK_DATA_DIR` set to that directory. No `--reload`.
- Waits until `GET http://127.0.0.1:<port>/api/me` returns 401. That is the app's answer once it can read the database. 200 would mean a cookie this check does not send.

Ready means `/api/me` is 401 and, after a drive starts, `main.editor[data-ready="1"]` is visible, `document.fonts.ready` has resolved, and the sheet width matches the desk (the same check as `MEASURED` in `tests/conftest.py`). A 401 by itself is not an editor.

The built frontend must exist at `src/blattwerk/static/index.html`. `mise run build` writes it. Launch does not build.

`python -m blattwerk invite --admin` prints `/einladung/<token>` against the same data directory. The drive opens that path, fills E-Mail and Passwort (at least 8 characters), and presses `Konto anlegen`. The password in the script is `verify-blatt`. The account exists only in the throwaway database.

## Doctor

```sh
uv run python .cursor/skills/verify-blattwerk/drive.py doctor
```

Run this before a drive whenever something looks wrong. It exits non-zero unless all of these hold:

- The recorded pid is alive and its command line is `uvicorn blattwerk.app:app` on the recorded port.
- That process's `BLATTWERK_DATA_DIR` is the recorded directory, and the directory is under `/tmp/blattwerk-verify/data/`.
- `GET /api/me` on `127.0.0.1` returns 401.
- `src/blattwerk/static/index.html` exists.

The report is `/tmp/blattwerk-verify/evidence/<run-id>/doctor.txt`.

## Drive

Headless Chromium, viewport 1400×1000, clipboard-read and clipboard-write granted. Default theme is Blattform (`localStorage.theme` absent, so `leaf`). At this width the insert controls are the left toolbar `Einfügen`, and Kopieren / Einfügen sit in the header bar.

```sh
uv run python .cursor/skills/verify-blattwerk/drive.py drive editor
uv run python .cursor/skills/verify-blattwerk/drive.py drive clipboard
```

`drive` runs doctor first and will not touch a server it did not record.

Editor pass: sign up, `Neues Blatt`, `Beenden` on the Rundgang if it is there, `Text` in the toolbar `Einfügen`, type `Hallo`, `F2`, wait until the header status has been `Speichert …` and then `Gespeichert`, reload, read the block back, `GET /api/sheets/<id>` and require the stored text `Hallo`.

Clipboard pass: the same steps, then `Kopieren`, `Einfügen` (two blocks), then `Control+c`, `Control+v` (three blocks). Reload and the sheet JSON must both show `Hallo` three times.

WebKit pass, which uses the pytest `editor` fixture (API user and API sheet, then the page) rather than the signup form:

```sh
uv run python .cursor/skills/verify-blattwerk/drive.py webkit \
  tests/test_keys.py::test_enter_and_f2_open_a_text_with_all_of_it_picked \
  tests/test_clipboard.py::test_the_button_ausschneiden_cuts
```

That is `mise run test:webkit -- -n 0 --tb=short` plus those node ids. Pass node ids. Do not use `-k`.

Selectors and the per-feature steps are in `features/`.

## Evidence

Proof goes to `/tmp/blattwerk-verify/evidence/<run-id>/`. Cleanup does not delete that directory.

- `doctor.txt` — pid, origin, data dir, `/api/me` status.
- `server.log` — uvicorn.
- `editor/` and `clipboard/` — `before-reload.png`, `after-reload.png`, matching `.aria.txt` snapshots of `main.editor`, `sheet.json` from `GET /api/sheets/<id>`, `result.txt` with the actions taken. A failed drive also leaves `failure.png` when the page was still open.
- `webkit.log` — the WebKit pytest output when `prove` or a multi-id `webkit` call runs.
- `summary.txt` — written by `prove` after cleanup.

A UI proof is the action in `result.txt`, the aria snapshot (the paragraphs are the words on the sheet), the screenshot, and `sheet.json` after reload. The header status `Gespeichert` alone is not the proof. After a reload nothing is selected, so Kopieren is disabled; the three `Hallo` paragraphs are the proof.

The WebKit log proves those node ids in WebKit. It does not prove the signup form, and it does not prove the rest of `tests/`.

## Cleanup

```sh
uv run python .cursor/skills/verify-blattwerk/drive.py cleanup
```

Sends SIGTERM to the process group of the recorded pid, SIGKILL if it is still alive after 5 seconds, and deletes only the recorded data directory under `/tmp/blattwerk-verify/data/`. It does not kill by process name and does not remove evidence. `prove` always cleans up, including when a drive fails.

## Helpers

`drive.py` is the only helper. It is executable. The invocations are the commands in Launch, Doctor, Drive, and Cleanup. `prove` is launch, doctor, `drive editor`, `drive clipboard`, the WebKit command above, cleanup, then a check that the evidence files, and not the data directory or the pid, remain.

## Keeping the map honest

When the editor's controls or the WebKit entry points move, run the vendored `/maintain-verification-skill` (`.cursor/skills/maintain-verification-skill/SKILL.md`) against this skill. A full WebKit run, outside `prove`, is `mise run test:webkit`.
