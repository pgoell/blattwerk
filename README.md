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

1. `scripts/keep-prev.sh` tags the image of the running container as `blattwerk-blattwerk:prev`, if that container answers `/api/me`, a route that reads the database. It writes down the id of that image for step 11. First, before the build: here the running image surely still has its name, and nothing has had a chance to fail. Docker cannot tag an image that has no name left.
2. Build the image as `blattwerk-blattwerk:canary`. `latest` still names the image that runs. The step ends after 15 minutes, so a stalled download fails the job. The old container keeps running.
3. Start the canary: `scripts/canary.sh start` copies the data folder to `~/.local/share/blattwerk-canary/` (mode 700; the database through SQLite's backup, read only) and runs the new image there as the container `blattwerk-canary`. The canary never gets the live folder: the script refuses a copy folder that is the live folder, lies inside it or holds it. The canary is not on the proxy's network and has no port, so nobody outside reaches it.
4. Smoke test the canary: `scripts/smoke.py` signs a smoke user up, opens a sheet, types, saves, loads the sheet again and finds the text, prints the PDF and counts its pages, and fetches the JS bundle. The smoke user lives in the copy only.
5. Remove the canary and the copy, whether the test passed or failed. The next deploy clears them too, in case a job was killed.
6. `scripts/snapshot.py` copies the database to `~/.local/share/blattwerk-backups/pre-<sha>.db`, where `<sha>` is the commit it deploys. It keeps the newest 30 snapshots.
7. Name the tested image `latest`: `docker tag blattwerk-blattwerk:canary blattwerk-blattwerk:latest`. Only an image that passed the canary gets that name.
8. `docker compose up -d --no-build` replaces the container. Up to here the live site has not changed. The step after it fails the deploy if the container does not run the image the canary tried.
9. Wait until the new container answers `/api/me`.
10. Smoke test live, read only: three GETs, no user and no write. `/` must give the page, the script that page names must come as JavaScript, and `/api/me` without a cookie must give 401, which the app says only after it has read the database. The database the container sees must also hold at least one user. On a new machine with no user yet, make the admin with the line from "Accounts" and rerun.
11. If step 7, 8, 9 or 10 fails or is cancelled, `scripts/go-back.sh` puts the `prev` image back and the run fails. It changes the image only, never the database: if the failed deploy moved the schema, follow "Going back" below. In four cases it changes nothing and says so, and a person decides then:
    - there is no `prev` image;
    - step 1 did not tag one in this run (the old container did not answer or its image had no name left, so `prev` is an older image);
    - `prev` no longer has the id that step 1 wrote down;
    - `prev` is the image that already runs (a rerun whose build came out of the cache, say), so there is nothing older to go back to. The container stays, and `latest` names the image that runs again.

Each step has a time limit of its own, and the job's limit lies above their sum. So the job's limit cannot end the run between step 8 and step 11.

A deploy that fails before step 7 (a failed canary, say) leaves the old container running, and `blattwerk-blattwerk:latest` still names the image that runs. `canary` names the failed image until the next build. A `docker compose up -d` by hand changes nothing then. Revert the commit and let the deploy run.

A rerun of the deploy of a commit from before the canary is no way back either: the workflow file comes from `master`, the scripts from that commit, which has no `scripts/canary.sh`. A rerun of a commit that has the canary but is older than the `canary` image name fails before the build: its `scripts/canary.sh` starts `latest`, so its canary would try the image that already runs and not the build. Revert on `master` instead.

The job log is public, so the steps print no token, no path of a user's file and no app logs. To see why a container failed: `docker logs blattwerk` on the VPS. The canary is gone by then; `docker run --rm blattwerk-blattwerk:canary` shows why an image does not start.

Step 3 or 6 can fail with "Open the site once and sign in, so the app mends it, then rerun". That happens when the app died in the middle of a write and left `blattwerk.db-journal` beside the database. The deploy reads the database read only and cannot mend it; the app's next write does. Open the site, sign in, then rerun the deploy.

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
