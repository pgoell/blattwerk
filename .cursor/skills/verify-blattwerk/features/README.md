# Blattwerk verification map

This directory is the maintained source for verifying the teacher-facing editor, paste and the clipboard, and the WebKit browser tests. Read the index before driving the app, then use the matching feature file as the recipe.

## Baseline preconditions

- Repo root is the working directory. `uv run python .cursor/skills/verify-blattwerk/drive.py` is the harness.
- `src/blattwerk/static/index.html` exists (`mise run build`).
- Launch uses a new `BLATTWERK_DATA_DIR` under `/tmp/blattwerk-verify/data/<run-id>/` and `http://localhost:<port>`.
- Do not set that variable to `~/.local/share/blattwerk/` or `~/.local/share/blattwerk-canary/`.
- Run `drive.py doctor` and require the recorded pid, data directory, and `401` from `/api/me`.
- Never drive a server this run did not start. `launch` refuses while one recorded pid is alive.

## Driving conventions

- Start every UI recipe from a fresh invite. Each invite link works once.
- Prefer the accessible names in the feature files over coordinates.
- Treat every command as literal. Keep the node ids and the flag `-n 0`.
- UI actions go through `drive.py`. WebKit actions go through `drive.py webkit` or `mise run test:webkit -- -n 0`.
- Count sheet blocks with `.block[data-id]`. Thumbnails also draw `.block` elements, without `data-id`.
- Reload with `page.reload`, then wait for `main.editor[data-ready="1"]`. Do not wrap `page.reload()` in `expect_response` and call `.finished()` on it.

## Proof and skip reporting

- Capture the user action and the resulting state, not only the final screen.
- UI proof includes an ARIA snapshot and a screenshot under `/tmp/blattwerk-verify/evidence/<run-id>/`.
- Mutation proof includes `GET /api/sheets/<id>` after a reload, in `sheet.json`.
- WebKit proof is the pytest log for the node id that was run. A green log for one node does not cover a node that was not named.
- Record the feature id and the entry point in `result.txt`.
- Report an unreachable path with the command that was run and the unmet precondition.
- Do not report a skipped entry point as verified through a different path.

## Feature entry contract

Each feature file starts with an H1 title and one paragraph describing the user-visible behavior. It then uses exactly four H2 sections in this order.

1. `Sub-features` lists short IDs with one line for each behavior.
2. `How to get to it (user POV)` lists every user entry point.
3. `Driving it with drive.py` starts with `Preconditions:` and uses labeled bullets that pair each user action with an exact command and observable result.
4. `Gotchas` lists traps that can waste or invalidate a verification run.

## Features

- [Editor](./editor.md) covers signup, a new sheet, inserting a text, typing, and reload.
- [Paste and clipboard](./paste-and-clipboard.md) covers Kopieren, Einfügen, and Control+C / Control+V on that text.
- [WebKit tests](./webkit-tests.md) covers the browser suite in WebKit for the editor keys and the cut/paste buttons.
