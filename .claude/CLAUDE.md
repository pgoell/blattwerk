# Blattomat: project instructions

Worksheet tool for Grundschule teachers

The product is called Blattomat. The repo, the Python package and the host `blattwerk.pgoell.com` still carry the old name `blattwerk`.

## Layout

- `src/blattwerk/`: FastAPI backend (accounts, feedback, SQLite), serves the built frontend from `static/`
- `frontend/`: React, TypeScript, Vite
- `tests/`: pytest

## Commands

mise owns every command. `mise tasks` lists them.

```sh
mise run test           # pytest, all cores
mise run test:one -- tests/test_keys.py::test_name    # one worker, stops at the first failure
mise run test:each -- tests/a.py::x tests/a.py::y    # one worker, runs each named test, failed or not
mise run test:flaky -- tests/test_keys.py::test_name  # 20 times side by side
mise run test:flaky -- 'tests/test_keys.py::test_name[param]'  # one parametrised case, 20 times
mise run test:webkit    # the browser tests in WebKit, in Docker where the host lacks its libraries
mise run test:webkit -- -n 0 -x tests/test_keys.py::test_name  # one of them
mise run test:native    # tests/test_native.py in a real window under xvfb; needs `uv run playwright install chromium` once
mise run test:native -- tests/test_native.py::test_name  # one of them; test:one and test:flaky deselect a native test
mise run test:model     # vitest and fast-check on the sheet model (frontend/src/*.test.ts), no browser; `mise run test` runs it too
mise run shot -- sheet.json out/                       # the editor and the PDF as PNG
mise run lint           # ruff check, ruff format --check, ty check, tsc, the schema's and the block pages' drift and descriptions
mise run eval           # tests/evals/ against claude -p through the MCP on a local server; on the subscription, not in CI
mise run eval -- uhr_lesen  # one task
mise run dev:api        # backend on :8000
mise run dev:web        # frontend dev server, proxies /api
mise run stage:up       # the live image on a copy of the live data, on 127.0.0.1:8220; prints a test teacher's login
mise run stage:down     # removes the stage's container and its copy
mise run teacher:page -- start             # a real window with a real mouse on the stage, under xvfb
mise run teacher:page -- hover Rückgängig  # one verb a call: click, drag, key, type, screenshot, pdf, stop
mise run build          # frontend into src/blattwerk/static
mise run fmt            # ruff format
mise run check-commits  # cocogitto on unpushed commits
```

A host without GTK runs `mise run test:webkit` in Docker. Keep a Chromium suite off that machine while those containers start and stop: one beside them has failed its console check with `net::ERR_NETWORK_CHANGED` (#256). Which part of Docker causes that is not proven.

A browser test takes the fixture `editor` (in `tests/conftest.py`) and the helpers in `tests/ui.py`; the recipe at the top of `ui.py` shows one whole test.
In a test the app's database does not wait for the disk (`unsynced` in `tests/conftest.py`), an `expect` waits up to 5 s, and `editor` gives the page once its fonts are in.
After a reload wait with `ui.reload(page, address)`, never with `page.reload()` inside `expect_response` and `.finished()` after: that hangs when it catches an answer of the old page.
A probe lives in `tests/probe_*.py` (git ignores it), imports from `ui`, and runs by node id through `test:one`, never with `-k`.

## Conventions

- Conventional Commits (`feat:`, `fix:`, `chore:` ...). The `commit-msg` hook rejects anything else.
- A new block type or prop needs a TSDoc description on each field, then `mise run schema`; a new kind of task also needs a recipe in `docs/okf/recipes/` (or the type on `no-recipe-yet.txt` there, on purpose). A hand-written page in `docs/okf/` whose `covers` names a changed type fails until you read it and bump its `generated.at`. A change to the MCP tools or to `frontend/src/sheet.tsx`: run `mise run eval` and put the score before and after in the PR.
- The `pre-push` hook runs lint and the commit check only. It does not run the suite: run `mise run test` before a push.
- Default branch is `master`. With branch protection applied (`mise run repo:apply-settings`), changes land through PRs that pass Lint, Test and Commits.
- A hook (`.claude/hooks/fence.py`) refuses Bash commands that skip checks, force push, change the repo settings, start, stop or remove docker containers and images, or write under `~/.local/share/blattwerk/` or the deploy's copy `~/.local/share/blattwerk-canary/`. Read the live data only: `sqlite3 -readonly`, or copy it elsewhere first.
- Bring master into a pushed branch with `git merge origin/master`, never a rebase: the fence refuses the force push a rebase needs.
- Way back if the hook itself breaks and refuses every Bash and Edit call: no session can mend it, so in a terminal outside Claude Code delete the `hooks` block from `.claude/settings.json` (or bring back a good one: `git checkout origin/master -- .claude/hooks/fence.py`), then start a new session.
- This project was generated from `gh:pgoell/project-template`. Update with `uvx copier update`.

## Subagents in a worktree

Claude Code refuses a Bash call it cannot prove stays inside the worktree. In a worktree-isolated subagent:

- Write new files with the Write tool and add to a file with Edit, never `cat > file <<EOF` or `cat >> file <<EOF`.
- Several tests: one call, `mise run test:each -- tests/a.py::x tests/a.py::y`, never a `for` loop.
- Run git as its own Bash call: no `&&` chain, no loop, no `cd` to the shared checkout.
- Give `mise`, `uv`, `sed` and `git` literal arguments, not shell variables or `for` loops.
