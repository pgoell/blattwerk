#!/usr/bin/env bash
# The deploy, as it runs on the VPS: prev, canary on a copy of the data, smoke test, snapshot,
# `latest`, up, the check of the image, the live smoke test, and the way back after a fail.
#   deploy.sh <commit sha>
#
# No workflow runs this. The deploy job sends a commit sha over SSH, and the key it uses is bound
# to server-infra's deploy/deploy.sh, which checks the sha and calls the copy of this script that
# lies there, beside copies of the scripts it calls and a compose file with no `build`. So nothing
# of a commit runs on the box but its image. After a change to one of these scripts, copy it over.
#
# smoke.py is not copied: it runs inside the container, on stdin, and comes out of the image it
# tests.
#
# The output lands in a public job log. No path of a user's file, no token and no app log.
set -euo pipefail

sha="${1:?usage: deploy.sh <commit sha>}"
here=$(cd "$(dirname "$0")" && pwd)
# The compose file lies one folder up, here and in the repo.
cd "$here/.."

image=ghcr.io/pgoell/blattwerk
live=/home/pascal/.local/share/blattwerk
copy=/home/pascal/.local/share/blattwerk-canary
backups=/home/pascal/.local/share/blattwerk-backups

# A folder of their own for the scripts: canary.sh reads smoke.py from beside itself.
work=$(mktemp -d)
cp "$here"/{alive.sh,canary.sh,go-back.sh,keep-prev.sh,same-image.sh,snapshot.py} "$work/"
# keep-prev.sh writes here what go-back.sh needs to know.
export GITHUB_OUTPUT=$work/output
: >"$GITHUB_OUTPUT"

# After a fail from the tag step on, `latest` has moved, even if `up` never
# ran. Before it the old container is untouched and there is nothing to go
# back from.
promoted=
finish() {
  status=$?
  trap - EXIT
  if [[ $status != 0 && -n $promoted ]]; then
    # Empty when keep-prev left an older `prev` in place.
    PREV_KEPT=$(sed -n 's/^kept=//p' "$GITHUB_OUTPUT") \
      PREV_IMAGE=$(sed -n 's/^image=//p' "$GITHUB_OUTPUT") \
      timeout 3m bash "$work/go-back.sh" || true
  fi
  rm -rf "$work"
  exit "$status"
}
trap finish EXIT

# First, before the pull: here the running image surely still has its name
# `latest`, and nothing has had a chance to fail yet.
timeout 2m bash "$work/keep-prev.sh"

# The pulled image gets the name the scripts know, so `latest` still names the
# image that runs. The registry's name goes again: the commit shas would pile up.
timeout 15m docker pull -q "$image:$sha" >/dev/null
docker tag "$image:$sha" blattwerk-blattwerk:canary
docker rmi "$image:$sha" >/dev/null
# Read inside a container, so that a link in the image cannot name a file of
# this box.
if ! docker run --rm --network none --entrypoint cat blattwerk-blattwerk:canary /app/scripts/smoke.py >"$work/smoke.py"; then
  echo "::error::the image holds no /app/scripts/smoke.py, so nothing can try it"
  exit 1
fi

# The new image runs on a copy of the data, off the proxy's network and with no
# port. The canary and the copy go again, pass or fail.
passed=yes
timeout 3m bash "$work/canary.sh" start "$live" "$copy" &&
  timeout 5m bash "$work/canary.sh" smoke || passed=no
timeout 2m bash "$work/canary.sh" stop "$live" "$copy"
[[ $passed == yes ]] || exit 1

# A schema move runs on the first request after a deploy and has no way back.
timeout 3m python3 "$work/snapshot.py" "$live/blattwerk.db" "$backups" "$sha"

# Only now, after the canary passed.
promoted=yes
docker tag blattwerk-blattwerk:canary blattwerk-blattwerk:latest
timeout 3m docker compose up -d --no-build

# Were compose to keep the old container, every check below would pass on the old image.
timeout 1m bash "$work/same-image.sh"

answers=
for _ in $(seq 1 30); do
  if bash "$work/alive.sh" blattwerk; then
    answers=yes
    break
  fi
  sleep 2
done
if [[ -z $answers ]]; then
  echo "::error::blattwerk did not answer on :8000. On the VPS: docker logs blattwerk"
  exit 1
fi
echo "blattwerk answers"

# Three GETs and one read of the database, which must hold a user. No smoke
# user and no write.
timeout 2m docker exec -i blattwerk /app/.venv/bin/python - --read-only http://127.0.0.1:8000 <"$work/smoke.py"

# Not after a fail: the failed image stays for a look, under the name `canary`
# until the next deploy.
docker image prune -f >/dev/null
echo "blattwerk runs $sha"
