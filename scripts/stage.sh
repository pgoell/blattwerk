#!/usr/bin/env bash
# The image that runs live, on a copy of the live data and a local port, with a test teacher.
#   stage.sh up
#   stage.sh down
set -euo pipefail

here=$(dirname "$0")
name=blattwerk-stage
image=blattwerk-blattwerk:latest
port=8220
share=$HOME/.local/share

# Sets `live`, `backups` and `copy` to real paths, or ends the run. The paths are fixed: the
# stage's volume and the `rm -rf` below take `copy` only, so no argument and no symlink can point
# them at the live data or its backups.
check() {
  if [ -L "$share/$name" ]; then refuse; fi
  live=$(realpath -m -- "$share/blattwerk")
  backups=$(realpath -m -- "$share/blattwerk-backups")
  copy=$(realpath -m -- "$share/$name")
  if [ "$(basename "$copy")" != "$name" ]; then refuse; fi
  for kept in "$live" "$backups"; do
    # The same folder, or one inside the other.
    case "$copy/" in "$kept/"*) refuse ;; esac
    case "$kept/" in "$copy/"*) refuse ;; esac
  done
}

refuse() {
  echo "stage: the copy folder must be a real folder named $name, apart from the live folder and the backups" >&2
  exit 1
}

remove() {
  docker rm -f "$name" >/dev/null 2>&1 || true
  if ! rm -rf -- "$copy" 2>/dev/null; then
    echo "stage: the copy of the data is still there: $copy" >&2
    exit 1
  fi
}

if [ $# -ne 1 ]; then set -- usage; fi
case "$1" in
  up)
    check
    # Before anything goes: in the middle of a deploy a stage that runs stays as it is.
    if ! docker image inspect "$image" >/dev/null 2>&1; then
      echo "stage: there is no image $image. A deploy builds it." >&2
      exit 1
    fi
    # Whatever fails from here on, the container and the copy go again. A signal too: alone it
    # would reach the EXIT trap with the 0 of the last command that ended.
    trap 'exit 130' INT TERM HUP
    trap 'if [ $? -ne 0 ]; then remove; fi' EXIT
    # An old stage goes first, so the copy is fresh and its port is free.
    remove
    if [ -n "$(ss -Hltn "sport = :$port")" ]; then
      echo "stage: port $port is taken. Free it, then run stage:up again." >&2
      exit 1
    fi
    mkdir -m 700 "$copy"
    if ! find "$live" -mindepth 1 -maxdepth 1 ! -name 'blattwerk.db*' \
      -exec cp -a -t "$copy" {} +; then
      echo "stage: the copy of the data folder failed" >&2
      exit 1
    fi
    python3 - "$live/blattwerk.db" "$copy/blattwerk.db" <<'PY'
import sqlite3
import sys
from pathlib import Path

source, target = Path(sys.argv[1]), sys.argv[2]
if not source.exists():
    sys.exit(0)
try:
    uri = f"{source.as_uri()}?mode=ro"
    src = sqlite3.connect(uri, uri=True, timeout=30, isolation_level=None)
    dst = sqlite3.connect(target)
    try:
        # The read takes the lock, and waits for a writer no longer than the timeout.
        # backup() alone would wait for ever.
        src.execute("BEGIN")
        src.execute("SELECT count(*) FROM sqlite_master").fetchone()
        src.backup(dst)
        src.execute("COMMIT")
    finally:
        src.close()
        dst.close()
except Exception as error:
    print(f"stage: the copy of the database failed: {error}", file=sys.stderr)
    if "readonly" in str(error):
        # The app died in the middle of a write and left its journal. Only a writer can mend that.
        print("Open the site once and sign in, so the app mends it, then rerun.", file=sys.stderr)
    sys.exit(1)
PY
    # One port, on this machine only. No network of the proxy, so no name on the web leads here,
    # and no restart: after a reboot the stage is gone until someone asks for it.
    if ! docker run -d --name "$name" -p "127.0.0.1:$port:8000" -v "$copy:/data" "$image" >/dev/null; then
      echo "stage: docker did not start the container" >&2
      exit 1
    fi
    end=$((SECONDS + ${ALIVE_WAIT:-60}))
    until bash "$here/alive.sh" "$name"; do
      if ((SECONDS >= end)); then
        echo "stage: the container did not answer on :8000 and is removed by now. To see why the image does not start: docker run --rm $image" >&2
        exit 1
      fi
      sleep 1
    done
    # The invite is a secret: it goes through the environment, never on a command line.
    if ! STAGE_INVITE=$(docker exec "$name" /app/.venv/bin/python -m blattwerk invite 2>/dev/null); then
      echo "stage: the container made no invite for the test teacher" >&2
      exit 1
    fi
    export STAGE_INVITE
    # The teacher script prints the login, and nothing else on stdout.
    if ! login=$(docker exec -i -e STAGE_INVITE "$name" /app/.venv/bin/python - http://127.0.0.1:8000 <"$here/stage-teacher.py"); then
      echo "stage: the test teacher could not sign up" >&2
      exit 1
    fi
    echo "URL: http://127.0.0.1:$port"
    echo "$login"
    ;;
  down)
    check
    remove
    echo "the stage is gone"
    ;;
  *)
    echo "usage: stage.sh up|down" >&2
    exit 2
    ;;
esac
