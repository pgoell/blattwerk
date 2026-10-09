#!/usr/bin/env bash
# Puts the `prev` image back after a deploy that failed once the new container was up.
set -euo pipefail

here=$(dirname "$0")

if ! docker image inspect blattwerk-blattwerk:prev >/dev/null 2>&1; then
  echo "::error::no prev image to go back to, so nothing was changed: the new container stays. On the VPS: docker logs blattwerk"
  exit 1
fi

docker tag blattwerk-blattwerk:prev blattwerk-blattwerk:latest
docker compose up -d --no-build
# The image only: the database keeps the shape the new code gave it.
echo "::error::the deploy failed and went back to the prev image. If this deploy moved the schema, the old image alone is not enough: README, \"Going back\"."

end=$((SECONDS + ${ALIVE_WAIT:-60}))
until bash "$here/alive.sh" blattwerk; do
  if ((SECONDS >= end)); then
    echo "::error::the prev image does not answer either. On the VPS: docker logs blattwerk"
    exit 1
  fi
  sleep 1
done
echo "blattwerk answers on the prev image"
