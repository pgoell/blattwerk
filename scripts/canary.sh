#!/usr/bin/env bash
# The new image on a copy of the data, before the deploy touches the live container.
#   canary.sh start <live-folder> <copy-folder>
#   canary.sh smoke
#   canary.sh stop <live-folder> <copy-folder>
set -euo pipefail

here=$(dirname "$0")
name=blattwerk-canary

# Sets `live` and `copy` to real paths, or ends the run. The canary's volume and the `rm -rf`
# below take `copy` only, so a wrong argument or a symlink can never point them at the live data.
check() {
  if [ -z "$1" ] || [ -z "$2" ]; then refuse; fi
  live=$(realpath -m -- "$1")
  copy=$(realpath -m -- "$2")
  if [ "$(basename "$copy")" != "$name" ]; then refuse; fi
  # The same folder, or one inside the other.
  case "$copy/" in "$live/"*) refuse ;; esac
  case "$live/" in "$copy/"*) refuse ;; esac
}

refuse() {
  echo "::error::canary: the copy folder must be named $name and lie apart from the live folder"
  exit 1
}

remove() {
  docker rm -f "$name" >/dev/null 2>&1 || true
  rm -rf -- "$copy"
}

case "${1:-}" in
  start)
    check "${2:-}" "${3:-}"
    # A killed run may have left both.
    remove
    mkdir -m 700 "$copy"
    # No output of cp: it would name the users' files in a public log.
    if ! find "$live" -mindepth 1 -maxdepth 1 ! -name 'blattwerk.db*' \
      -exec cp -a -t "$copy" {} + 2>/dev/null; then
      echo "::error::canary: the copy of the data folder failed"
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
    # The job log is public: an OSError's own text would name the path.
    reason = error.strerror if isinstance(error, OSError) else str(error)
    print(f"::error::canary: the copy of the database failed: {reason}")
    if "readonly" in str(error):
        # The app died in the middle of a write and left its journal. Only a writer can mend that.
        print("Open the site once and sign in, so the app mends it, then rerun.")
    sys.exit(1)
PY
    # No network of the proxy and no port: only `docker exec` reaches the canary.
    docker run -d --name "$name" -v "$copy:/data" blattwerk-blattwerk:latest >/dev/null
    end=$((SECONDS + ${ALIVE_WAIT:-60}))
    until bash "$here/alive.sh" "$name"; do
      if ((SECONDS >= end)); then
        # No `docker logs` hint: the stop that follows removes the container at once.
        echo "::error::the canary did not answer on :8000 and is removed by now. On the VPS, to see why the image does not start: docker run --rm blattwerk-blattwerk:latest"
        exit 1
      fi
      sleep 1
    done
    echo "the canary answers"
    ;;
  smoke)
    # The invite is a secret: it goes through the environment, never on a command line or to the log.
    if ! SMOKE_INVITE=$(docker exec "$name" /app/.venv/bin/python -m blattwerk invite 2>/dev/null); then
      echo "::error::the canary made no invite for the smoke user"
      exit 1
    fi
    export SMOKE_INVITE
    docker exec -i -e SMOKE_INVITE "$name" /app/.venv/bin/python - http://127.0.0.1:8000 <"$here/smoke.py"
    ;;
  stop)
    check "${2:-}" "${3:-}"
    remove
    ;;
  *)
    echo "usage: canary.sh start|stop <live-folder> <copy-folder>, canary.sh smoke" >&2
    exit 2
    ;;
esac
