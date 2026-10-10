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
mise run test:flaky -- tests/test_keys.py::test_name  # 20 times side by side
mise run test:flaky -- 'tests/test_keys.py::test_name[param]'  # one parametrised case, 20 times
mise run test:webkit    # the browser tests in WebKit, in Docker where the host lacks its libraries
mise run test:webkit -- -n 0 -x tests/test_keys.py::test_name  # one of them
mise run test:native    # tests/test_native.py in a real window under xvfb; needs `uv run playwright install chromium` once
mise run shot -- sheet.json out/                       # the editor and the PDF as PNG
mise run lint           # ruff check, ruff format --check, ty check, tsc
mise run dev:api        # backend on :8000
mise run dev:web        # frontend dev server, proxies /api
mise run build          # frontend into src/blattwerk/static
mise run fmt            # ruff format
mise run check-commits  # cocogitto on unpushed commits
```

A browser test takes the fixture `editor` (in `tests/conftest.py`) and the helpers in `tests/ui.py`; the recipe at the top of `ui.py` shows one whole test.
A probe lives in `tests/probe_*.py` (git ignores it), imports from `ui`, and runs by node id through `test:one`, never with `-k`.

## Conventions

- Conventional Commits (`feat:`, `fix:`, `chore:` ...). The `commit-msg` hook rejects anything else.
- The `pre-push` hook runs lint and the commit check only. It does not run the suite: run `mise run test` before a push.
- Default branch is `master`. With branch protection applied (`mise run repo:apply-settings`), changes land through PRs that pass Lint, Test and Commits.
- A hook (`.claude/hooks/fence.py`) refuses Bash commands that skip checks, force push, change the repo settings, start, stop or remove docker containers and images, or write under `~/.local/share/blattwerk/` or the deploy's copy `~/.local/share/blattwerk-canary/`. Read the live data only: `sqlite3 -readonly`, or copy it elsewhere first.
- Way back if the hook itself breaks and refuses every Bash and Edit call: no session can mend it, so in a terminal outside Claude Code delete the `hooks` block from `.claude/settings.json` (or bring back a good one: `git checkout origin/master -- .claude/hooks/fence.py`), then start a new session.
- This project was generated from `gh:pgoell/project-template`. Update with `uvx copier update`.
