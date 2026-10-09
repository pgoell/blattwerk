#!/usr/bin/env bash
# Tags the image of the running container as `prev`, so a deploy leaves a way back.
set -euo pipefail

if ! image=$(docker inspect -f '{{.Image}}' blattwerk 2>/dev/null); then
  echo "no blattwerk container, nothing to keep"
  exit 0
fi

# After a failed deploy the running container is the broken one. A rerun must not put it in the
# place of the good `prev`. alive.sh asks a route that reads the database: `/` answers without it.
if ! bash "$(dirname "$0")/alive.sh" blattwerk; then
  echo "::warning::the running blattwerk container does not answer, so prev stays as it is"
  exit 0
fi

docker tag "$image" blattwerk-blattwerk:prev
image=${image#sha256:}
echo "prev is ${image:0:12}"
