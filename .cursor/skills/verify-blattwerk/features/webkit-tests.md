# WebKit tests

`mise run test:webkit` runs the browser tests in WebKit. The editor keys and the cut, copy and paste buttons are part of that suite. The fixture opens the built frontend as a signed-in teacher and drives it with clicks and keys.

## Sub-features

- `webkit-editor` opens a text with Enter and with F2, then types over it.
- `webkit-clipboard` cuts with `Ausschneiden` and pastes with `Einfügen`, with a mouse and with a touch pointer.
- `webkit-suite` is the whole browser suite in WebKit. `prove` does not run it.

## How to get to it (user POV)

- A teacher presses Enter or F2 on a selected text and types. That is `tests/test_keys.py`.
- A teacher presses `Ausschneiden` and `Einfügen`. That is `tests/test_clipboard.py`.
- The signup form and `Neues Blatt` are not these tests. The fixture creates the user and the sheet through the API, then the page is the editor. The teacher-shaped signup path is [Editor](./editor.md).

## Driving it with drive.py

Preconditions:

- `src/blattwerk/static/index.html` is current. `mise run test:webkit` depends on `build`.
- WebKit's browser is installed (`uv run playwright install webkit` once) and launches. On a host whose `ldconfig -p` lists `libgtk-4.so.1`, `scripts/test-webkit.sh` runs `uv run pytest` on the host. Without that library, and with docker, the script runs the same pytest inside `mcr.microsoft.com/playwright:v1.64.0-noble`. `libgtk-4.so.1` only chooses the branch. A download that prints Playwright's missing-dependency warning does not launch until those libraries are installed.
- Node ids, not `-k`. One worker: `-n 0`.

- **Editor keys.** Run the node id below. The four cases are Enter/F2 and text/shape. Each case selects the block, presses the key, types, and the field shows the new word. Exit code 0.
- **Cut and paste buttons.** Run the node id below. The cases are `mouse` and `touch`. `Ausschneiden` removes the selected shape, `Einfügen` brings it back, and the stored props match. Exit code 0.
- **Proof.** The pytest log. `prove` writes `/tmp/blattwerk-verify/evidence/<run-id>/webkit.log`. A standalone `webkit` call with one node id writes `webkit-<test-name>.log` in the active evidence directory, or in `/tmp/blattwerk-verify/evidence/webkit-only` when no server is recorded.

```sh
uv run python .cursor/skills/verify-blattwerk/drive.py webkit \
  tests/test_keys.py::test_enter_and_f2_open_a_text_with_all_of_it_picked \
  tests/test_clipboard.py::test_the_button_ausschneiden_cuts
```

The whole suite, which this map does not treat as already run:

```sh
mise run test:webkit
```

## Gotchas

- These tests do not exercise `/einladung` or `Neues Blatt`. A green WebKit log is not proof of signup.
- A green run of `test_the_button_ausschneiden_cuts` does not cover a picture pasted from another app. That path is `test_the_button_einfuegen_pastes_a_picture_by_touch` and `test_einfuegen_pastes_a_picture_from_another_app`.
- The fixture sets `localStorage.tour`, grants clipboard-read (and clipboard-write except on WebKit), and clears clipboard text when the editor opens. A drive that skips those steps is a different setup.
- `BLATTWERK_BROWSER=webkit` is set by `scripts/test-webkit.sh`. Exporting it yourself and calling `uv run pytest` is the same browser only when the host has the WebKit binary and the libraries Playwright names. Otherwise the shell script is the entry point, and it still needs those libraries when it chooses the host.
- `-n auto` is the default in `pyproject.toml`. Pass `-n 0` so one worker owns the browser.
- Do not describe a node that was not in the command as passed.
