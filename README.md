# Blattomat

Worksheet tool for Grundschule teachers

The product is called Blattomat. The repo, the Python package and the host `blattwerk.pgoell.com` still carry the old name `blattwerk`.

## Setup

Needs [mise](https://mise.jdx.dev).

```sh
mise install      # python, uv, lefthook, cocogitto, jq
mise run install  # git hooks, dependencies and the Chromium that prints the PDF
mise run test
mise run lint     # ruff + ty
```

Commit messages follow [Conventional Commits](https://www.conventionalcommits.org); the `commit-msg` hook checks them with cocogitto.

## Layout

- `src/blattwerk/`: FastAPI backend. `auth.py` (accounts), `feedback.py`, `db.py` (SQLite), `maths.py` (the exercise generator), `pdf.py` (the PDF export), `app.py` (legal pages and the built frontend).
- `frontend/`: React, TypeScript and Vite. `npm run build` writes to `src/blattwerk/static/`, which FastAPI serves.

## Run it

```sh
mise run dev:api   # backend on :8000
mise run dev:web   # frontend on :5173, proxies /api to the backend
```

## Accounts

Sign-up is by invite only. An admin makes invite and password links on `/admin` and sends them by hand. Links work once and die after 7 days.

The first admin comes from the command line:

```sh
python -m blattwerk invite --admin   # prints /einladung/<token>
```

On the VPS:

```sh
docker compose exec blattwerk /app/.venv/bin/python -m blattwerk invite --admin
```

## PDF

`GET /api/sheets/<id>/pdf` starts headless Chromium (Playwright), which prints the page `/druck/<id>` of this same server over loopback. `?solved=true` gives the answer key. Chromium has no session. It sends a token in the `X-Render-Token` header, signed for that one sheet and good for a minute. The token opens the sheet's document and the pictures on it, and nothing else.

Chromium prints the built frontend, so `mise run test` builds it first, and a PDF from the dev servers shows the last `mise run build`.

## Feedback

`/feedback` takes written or spoken feedback, `/feedback/fotos` takes photos of sheets, one sheet or Klassenarbeit per send. Each send lands in its own folder under `users/<id>/feedback/` in `BLATTWERK_DATA_DIR` (`feedback.json`, `audio-N.*`, `photo-N.*`). Deleting the account deletes the folder.

## Deploy

A push to `master` deploys to `blattwerk.pgoell.com` once CI is green. `.github/workflows/deploy.yml` runs on the VPS's own runner (`server-infra/runners`): it builds the image from that commit, restarts the container and fails if the app does not answer.

By hand, on the VPS:

```sh
docker compose up -d --build
```

The database (`blattwerk.db`) and the uploads live in `~/.local/share/blattwerk/`, outside the repo.

Before the build, the deploy makes a way back:

- `scripts/snapshot.py` copies the database to `~/.local/share/blattwerk-backups/pre-<sha>.db`, where `<sha>` is the commit it deploys. It keeps the newest 30 snapshots. If the copy fails, the deploy stops.
- `scripts/keep-prev.sh` tags the running image as `blattwerk-blattwerk:prev`.

### Going back

Run these in the repo folder on the VPS.

To the old image:

```sh
docker tag blattwerk-blattwerk:prev blattwerk-blattwerk:latest && docker compose up -d --no-build
```

The next deploy builds from `master` again, so revert the commit too. `prev` moves on with each deploy whose running container answered.

To a snapshot:

```sh
docker compose stop
cp ~/.local/share/blattwerk/blattwerk.db ~/.local/share/blattwerk-backups/blattwerk-before-restore.db
rm -f ~/.local/share/blattwerk/blattwerk.db-journal
cp ~/.local/share/blattwerk-backups/pre-<sha>.db ~/.local/share/blattwerk/blattwerk.db
docker compose start
```

SQLite would replay a leftover `blattwerk.db-journal` into the restored file, so it has to go. Everything saved since the snapshot is lost. The snapshot holds no uploads; the hourly backup has them.

A deploy that moved the schema needs both: the database already has the new shape, and the old image alone does not undo that. Go back to the snapshot and to `prev`.
