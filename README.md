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

A test that fails now and then runs 20 times side by side, a parametrised one by its full id, in quotes because of the brackets:

```sh
mise run test:flaky -- tests/test_keys.py::test_name
mise run test:flaky -- 'tests/test_keys.py::test_name[param]'
```

Commit messages follow [Conventional Commits](https://www.conventionalcommits.org); the `commit-msg` hook checks them with cocogitto.

The `pre-push` hook runs `mise run lint` and the commit check, not the suite. Run `mise run test` yourself before a push; CI runs it on every pull request and is the gate for the merge.

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

Deleting an account deletes its folder `users/<id>/`. If the folder will not go after three tries, the table `leftovers` remembers it, each start tries again, and `/admin` shows an alert until it is gone.

## Pictures

A picture lies in `users/<id>/uploads/<n>` with a row in `uploads`. Once no sheet and no template of its owner has shown it for 30 days, the owner's next save deletes both. The file's time counts the days: each save that shows the picture or takes it away sets it, so undo and the clipboard can still bring a picture back.

## PDF

`GET /api/sheets/<id>/pdf` starts headless Chromium (Playwright), which prints the page `/druck/<id>` of this same server over loopback. `?solved=true` gives the answer key. Chromium has no session. It sends a token in the `X-Render-Token` header, signed for that one sheet and good for a minute. The token opens the sheet's document and the pictures on it, and nothing else.

Chromium prints the built frontend, so `mise run test` builds it first, and a PDF from the dev servers shows the last `mise run build`.

## Feedback

`/feedback` takes written or spoken feedback, `/feedback/fotos` takes photos of sheets, one sheet or Klassenarbeit per send. Each send lands in its own folder under `users/<id>/feedback/` in `BLATTWERK_DATA_DIR` (`feedback.json`, `audio-N.*`, `photo-N.*`). Deleting the account deletes the folder.

## Deploy

A push to `master` deploys to `blattwerk.pgoell.com` once CI is green. `.github/workflows/deploy.yml` runs on the VPS's own runner (`server-infra/runners`): it builds the image from that commit, tries it on a copy of the data, and only then replaces the running container.

By hand, on the VPS (no canary, no smoke test, no way back):

```sh
docker compose up -d --build
```

The database (`blattwerk.db`) and the uploads live in `~/.local/share/blattwerk/`, outside the repo.

The steps, in order. A step that fails stops the deploy.

1. Build the image. The step ends after 15 minutes, so a stalled download fails the job. The old container keeps running.
2. Start the canary: `scripts/canary.sh start` copies the data folder to `~/.local/share/blattwerk-canary/` (mode 700; the database through SQLite's backup, read only) and runs the new image there as the container `blattwerk-canary`. The canary never gets the live folder: the script refuses a copy folder that is the live folder, lies inside it or holds it. The canary is not on the proxy's network and has no port, so nobody outside reaches it.
3. Smoke test the canary: `scripts/smoke.py` signs a smoke user up, opens a sheet, types, saves, loads the sheet again and finds the text, prints the PDF and counts its pages, and fetches the JS bundle. The smoke user lives in the copy only.
4. Remove the canary and the copy, whether the test passed or failed. The next deploy clears them too, in case a job was killed.
5. `scripts/snapshot.py` copies the database to `~/.local/share/blattwerk-backups/pre-<sha>.db`, where `<sha>` is the commit it deploys. It keeps the newest 30 snapshots.
6. `scripts/keep-prev.sh` tags the image of the running container as `blattwerk-blattwerk:prev`, if that container answers `/api/me`, a route that reads the database.
7. `docker compose up -d` replaces the container. Up to here the live site has not changed.
8. Wait until the new container answers `/api/me`.
9. Smoke test live, read only: three GETs, no user and no write. `/` must give the page, the script that page names must come as JavaScript, and `/api/me` without a cookie must give 401, which the app says only after it has read the database.
10. If step 7, 8 or 9 fails, `scripts/go-back.sh` puts the `prev` image back and the run fails. It changes the image only, never the database: if the failed deploy moved the schema, follow "Going back" below. Without a `prev` image it changes nothing and says so.

The job log is public, so the steps print no token, no path of a user's file and no app logs. To see why a container failed: `docker logs blattwerk` on the VPS.

Step 2 or 5 can fail with "Open the site once and sign in, so the app mends it, then rerun". That happens when the app died in the middle of a write and left `blattwerk.db-journal` beside the database. The deploy reads the database read only and cannot mend it; the app's next write does. Open the site, sign in, then rerun the deploy.

### Going back

Run these in the repo folder on the VPS.

To the old image (what `scripts/go-back.sh` does after a failed deploy):

```sh
docker tag blattwerk-blattwerk:prev blattwerk-blattwerk:latest && docker compose up -d --no-build
```

The next deploy builds from `master` again, so revert the commit too. `prev` moves on with each deploy whose running container answered.

To a snapshot:

```sh
docker compose stop
aside=~/.local/share/blattwerk-backups/before-restore-$(date +%Y%m%d-%H%M%S)
mkdir -m 700 "$aside"
mv ~/.local/share/blattwerk/blattwerk.db* "$aside"/
cp ~/.local/share/blattwerk-backups/pre-<sha>.db ~/.local/share/blattwerk/blattwerk.db
docker compose start
```

The `mv` takes a leftover `blattwerk.db-journal` along: SQLite would replay it into the restored file. Everything saved since the snapshot is lost. The snapshot holds no uploads; the hourly backup has them. A snapshot older than 30 days may show a picture whose file a save has deleted since: take `users/` from a backup of the same day. After any restore of `users/` from a backup, the files carry their old times, so a picture that no sheet shows may go at its owner's next save.

A deploy that moved the schema needs both, in this order: the database already has the new shape, the old image alone does not undo that, and the new image would move a restored database again on its first request. Run the snapshot block up to the `cp`, then start the old image in place of `docker compose start`:

```sh
docker tag blattwerk-blattwerk:prev blattwerk-blattwerk:latest && docker compose up -d --no-build
```
