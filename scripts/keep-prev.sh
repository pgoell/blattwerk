#!/usr/bin/env bash
# Tags the image of the running container as `prev`, so a deploy leaves a way back.
set -euo pipefail

if ! image=$(docker inspect -f '{{.Image}}' blattwerk 2>/dev/null); then
  echo "no blattwerk container, nothing to keep"
  exit 0
fi

# After a failed deploy the running container is the broken one. A rerun must not put it in the
# place of the good `prev`. alive.sh asks a route that reads the database: `/` answers without it.
# Three tries: a good app that is busy for a moment must not leave an older image as `prev`.
answers=
for try in 1 2 3; do
  if [ "$try" != 1 ]; then sleep 1; fi
  if bash "$(dirname "$0")/alive.sh" blattwerk; then
    answers=yes
    break
  fi
done
if [ -z "$answers" ]; then
  echo "::warning::the running blattwerk container does not answer, so prev stays as it is"
  exit 0
fi

# A build without a deploy after it took the running image's name away, and docker cannot tag an
# image it has no name for. The deploy must go on all the same, or no deploy could ever mend it.
if ! docker tag "$image" blattwerk-blattwerk:prev 2>/dev/null; then
  echo "::warning::the running image has no name left to tag, so prev stays as it is"
  exit 0
fi
# go-back.sh goes back by itself only to a `prev` that this run tagged.
if [ -n "${GITHUB_OUTPUT:-}" ]; then echo "kept=yes" >>"$GITHUB_OUTPUT"; fi
image=${image#sha256:}
echo "prev is ${image:0:12}"
