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

The `pre-push` hook runs `mise run lint`, the commit check and `scripts/check-file-size`, not the suite. Run `mise run test` yourself before a push; CI runs it on every pull request and is the gate for the merge.

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

### The daily feedback job

Cron on the VPS runs `scripts/feedback-cron.sh` each morning. It reads every send it has not read before and turns it into an issue here, labelled `feedback` plus `bug` or `wish`, or into a comment on the open issue on the same point.

A send from the MCP tool `send_feedback` (an AI that hit a fault while building a sheet) gets the label `ai` as well, and its issue or comment says it came from an AI.

This repo is public and a send is private, so the work is split:

- The model reads one send (text and pictures, inline) and returns a verdict as JSON: bug, wish, question or nothing, a title, a body in its own words, an open issue it matches. It runs with no tool, no MCP server and no user settings: it cannot read a file, run a command or reach GitHub.
- Plain code (`scripts/feedback_triage.py`) does the rest. Before any write to GitHub, `scripts/feedback_privacy.py` checks title and body against every e-mail address in the users table and the names in them, user ids, the send's file names, links, class and school names, four words in a row copied from the send, and any capitalised word of the send (a name the teacher wrote). On a hit it files nothing and leaves the send for Pascal.
- No file of a send is ever uploaded. A voice note is not heard: the summary lists it under "To hear".

The job opens the data folder read only. Its own files live in `~/.local/share/blattwerk-feedback/` (mode 700): `read.json` (the sends already read), `pending.json` (the tries of a send that failed, and the cut-off folders already named), `summaries/<date>.md` (one a day, none on a day without a new send or a cut-off folder) and `cron.log`. A send that fails is tried again on the next run, up to five runs; then the summary says the job gave up on it. A gh write that gets no answer in time is not sent again. It stands on the summary, to look at on GitHub. Any failure counts as a try, also five mornings with the model signed out: to have a send read again, delete its key from `read.json`.

The check cannot know a name it has never seen: a child's name that stands only on a photo, or a name the teacher wrote without its capital. There the model's instructions are the only guard. Read the summary now and then.

Cron runs the shell file and the two Python files as `origin/master` has them, not as the checkout stands, so a half-built branch never runs against the live data. The crontab's line, and a dry run by hand from the repo:

```sh
15 5 * * * cd /home/pascal/Code/blattwerk && (git show origin/master:scripts/feedback-cron.sh | bash) >> /home/pascal/.local/share/blattwerk-feedback/cron.log 2>&1

git show origin/master:scripts/feedback-cron.sh | bash -s -- --dry-run   # prints what it would file; files nothing, writes nothing
```

On a new machine, make the folder before the cron line goes in: `mkdir -m 700 -p ~/.local/share/blattwerk-feedback`. Cron cannot open the log in a folder that is not there, and then the job never starts.

To stop the job, remove that line from the crontab.

## Deploy

A push to `master` deploys to `blattwerk.pgoell.com` once CI is green. `.github/workflows/deploy.yml` has two jobs, both on GitHub's own runners. The first builds the image from that commit and pushes it to GHCR as `ghcr.io/pgoell/blattwerk:<sha>`. The second sends the commit sha to the VPS over SSH, and nothing else. Its key is bound to one script there, `deploy/deploy.sh blattwerk` in server-infra, which reads the sha as an image tag. The VPS pulls that image, tries it on a copy of the data, and only then replaces the running container.

No file of a commit runs on the VPS, only its image. The scripts that run there are copies, in server-infra under `deploy/blattwerk/scripts/`: `deploy.sh`, which runs the steps below, and `keep-prev.sh`, `canary.sh`, `snapshot.py`, `same-image.sh`, `alive.sh` and `go-back.sh`, which it calls. The originals and their tests live here, in `scripts/` and `tests/`. A merge does not move the copies: after a change to one of them, copy it over by hand. `scripts/smoke.py` is not copied. The Dockerfile puts it into the image, and the deploy reads it out of the image it tests.

The compose file the deploy uses lies there too, `deploy/blattwerk/compose.yaml`. It names the image `blattwerk-blattwerk:latest` and has no `build`. The `docker-compose.yml` here has the same project and container name.

By hand, on the VPS, the whole deploy of a commit whose image is in GHCR (`<sha>` is the full commit sha):

```sh
SSH_ORIGINAL_COMMAND=<sha> ~/Code/server-infra/deploy/deploy.sh blattwerk
```

Or the image alone (no canary, no smoke test, no way back):

```sh
docker pull ghcr.io/pgoell/blattwerk:<sha>
docker tag ghcr.io/pgoell/blattwerk:<sha> blattwerk-blattwerk:latest
docker compose -f ~/Code/server-infra/deploy/blattwerk/compose.yaml up -d
```

The database (`blattwerk.db`) and the uploads live in `~/.local/share/blattwerk/`, outside the repo.

The steps of `scripts/deploy.sh`, in order. A step that fails stops the deploy.

1. `scripts/keep-prev.sh` tags the image of the running container as `blattwerk-blattwerk:prev`, if that container answers `/api/me`, a route that reads the database. It writes down the id of that image for step 11. First, before the pull: here the running image surely still has its name, and nothing has had a chance to fail. Docker cannot tag an image that has no name left.
2. Pull `ghcr.io/pgoell/blattwerk:<sha>` and name it `blattwerk-blattwerk:canary`. `latest` still names the image that runs. The pull ends after 15 minutes, so a stalled download fails the deploy. The old container keeps running. The step then reads `/app/scripts/smoke.py` out of the image, and fails if the image holds none.
3. Start the canary: `scripts/canary.sh start` copies the data folder to `~/.local/share/blattwerk-canary/` (mode 700; the database through SQLite's backup, read only) and runs the new image there as the container `blattwerk-canary`. The canary never gets the live folder: the script refuses a copy folder that is the live folder, lies inside it or holds it. The canary is not on the proxy's network and has no port, so nobody outside reaches it.
4. Smoke test the canary: `smoke.py` signs a smoke user up, opens a sheet, types, saves, loads the sheet again and finds the text, prints the PDF and counts its pages, and fetches the JS bundle. The smoke user lives in the copy only.
5. Remove the canary and the copy, whether the test passed or failed. The next deploy clears them too, in case a deploy was killed.
6. `scripts/snapshot.py` copies the database to `~/.local/share/blattwerk-backups/pre-<sha>.db`, where `<sha>` is the commit it deploys. It keeps the newest 30 snapshots.
7. Name the tested image `latest`: `docker tag blattwerk-blattwerk:canary blattwerk-blattwerk:latest`. Only an image that passed the canary gets that name.
8. `docker compose up -d --no-build` replaces the container. Up to here the live site has not changed. `scripts/same-image.sh` then fails the deploy if the image the container runs does not hold the same layers and the same config as the image the canary tried. It does not compare the ids: a build out of the cache (a commit that changes only tests, say) gets a new id for the same image, and compose keeps the container then.
9. Wait until the new container answers `/api/me`.
10. Smoke test live, read only: three GETs, no user and no write. `/` must give the page, the script that page names must come as JavaScript, and `/api/me` without a cookie must give 401, which the app says only after it has read the database. The database the container sees must also hold at least one user. On a new machine with no user yet, make the admin with the line from "Accounts" and rerun.
11. If step 7, 8, 9 or 10 fails, `scripts/go-back.sh` puts the `prev` image back and the deploy fails. It changes the image only, never the database: if the failed deploy moved the schema, follow "Going back" below. In four cases it changes nothing and says so, and a person decides then:
    - there is no `prev` image;
    - step 1 did not tag one in this run (the old container did not answer or its image had no name left, so `prev` is an older image);
    - `prev` no longer has the id that step 1 wrote down;
    - `prev` is the image that already runs (a rerun of the commit that is live, say), so there is nothing older to go back to. The container stays, and `latest` names the image that runs again.

The pull, each script, `up` and the live smoke test have a time limit of their own, and the limit of the deploy job lies above their sum. A job that is cancelled or loses its connection does not stop the script either: it runs to its end on the VPS. So nothing ends the run between step 8 and step 11.

A deploy that fails before step 7 (a failed canary, say) leaves the old container running, and `blattwerk-blattwerk:latest` still names the image that runs. `canary` names the failed image until the next deploy. A `docker compose up -d` by hand changes nothing then. Revert the commit and let the deploy run.

A rerun of the deploy of an older commit sends that commit's sha again. The scripts lie on the VPS and no longer come from the commit, so an old commit cannot bring an old canary along: its image goes through the same steps as any other. An image from before the Dockerfile copied `scripts/smoke.py` into it fails in step 2, because the script finds no smoke test in it. The live container is untouched then.

The job log is public, so the scripts print no token, no path of a user's file and no app logs. The VPS keeps what each deploy printed in `~/.local/state/deploy/blattwerk.log`. To see why a container failed: `docker logs blattwerk` on the VPS. The canary is gone by then; `docker run --rm blattwerk-blattwerk:canary` shows why an image does not start.

Step 3 or 6 can fail with "Open the site once and sign in, so the app mends it, then rerun". That happens when the app died in the middle of a write and left `blattwerk.db-journal` beside the database. The deploy reads the database read only and cannot mend it; the app's next write does. Open the site, sign in, then rerun the deploy.

### Going back

Run these on the VPS, in `~/Code/server-infra/deploy/blattwerk/`, where the compose file lies.

To the old image (what `scripts/go-back.sh` does after a failed deploy):

```sh
docker tag blattwerk-blattwerk:prev blattwerk-blattwerk:latest && docker compose up -d --no-build
```

The next deploy puts `master` live again, so revert the commit too. `prev` moves on with each deploy whose running container answered.

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

## Stage

The stage is the image that runs live, on a copy of the live data, for trying the app without touching a teacher's sheets. On the VPS:

```sh
mise run stage:up     # prints the URL and the login of a test teacher
mise run stage:down   # removes the container and the copy
```

`stage:up` copies `~/.local/share/blattwerk/` to `~/.local/share/blattwerk-stage/` (the database through SQLite's backup, read only) and runs `blattwerk-blattwerk:latest` there as the container `blattwerk-stage`. It answers on `http://127.0.0.1:8220`, a port of this machine only: it is not on the proxy's network, so no name on the web leads to it, and it does not restart by itself. It sits on docker's default bridge, where a container without a network of its own could reach it; none runs there today. The script writes nothing to the live folder or the backups, and refuses a copy folder that is a symlink, or that is one of the two, lies inside one or holds one.

The copy holds real data: every teacher's sheets and pictures. It has mode 700; remove it with `stage:down` when the work is done. The test teacher `teacher-run@stage.invalid` lives in the copy only, is no admin and sees no other account's sheets. Each `stage:up` makes a new password.

A running stage keeps the image it started with. After a deploy it still runs the old one: run `stage:up` again, which also takes a fresh copy.

`mise run teacher:page -- start` opens a real window on the stage, under xvfb, for what a headless browser cannot do: hover, drag, Shift+click, a slider, a colour picker. Each later call is one verb, such as `click PDF` or `hover 640,20`; it acts, writes the window to `/tmp/teacher-run/last.png` and prints that path. `stop` shuts the window. The verbs are listed at the top of `scripts/teacher-page.py`.
