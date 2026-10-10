#!/usr/bin/env bash
# Puts the `prev` image back after a deploy that failed once the new container was up.
set -euo pipefail

here=$(dirname "$0")

if ! prev=$(docker image inspect -f '{{.Id}}' blattwerk-blattwerk:prev 2>/dev/null); then
  echo "::error::no prev image to go back to, so nothing was changed: the new container stays. On the VPS: docker logs blattwerk"
  exit 1
fi

# The deploy sets PREV_KEPT, empty when keep-prev.sh left `prev` as it was: that image is older
# than the one that ran, and may not know the database. A person decides then. By hand it is unset.
if [ "${PREV_KEPT-yes}" != yes ]; then
  echo "::error::prev is not the image that ran before this deploy, so nothing was changed: the new container stays. README, \"Going back\"."
  exit 1
fi

# The deploy also hands over the id keep-prev.sh tagged. Another id: something moved `prev` since.
if [ -n "${PREV_IMAGE:-}" ] && [ "$prev" != "$PREV_IMAGE" ]; then
  echo "::error::prev is not the image that ran before this deploy (keep-prev tagged another id), so nothing was changed: the new container stays. README, \"Going back\"."
  exit 1
fi

# A rerun with a cached build: the build is the image that ran, so `prev` is what runs now. Or
# `up` never replaced the container. The container stays; `latest` gets the name of what runs
# again, so a `docker compose up -d` by hand changes nothing.
# No container at all: go on, `prev` is the best there is.
if running=$(docker inspect -f '{{.Image}}' blattwerk 2>/dev/null) && [ "$running" = "$prev" ]; then
  docker tag blattwerk-blattwerk:prev blattwerk-blattwerk:latest
  echo "::error::the deploy failed, and prev is the image that already runs: there is nothing older to go back to, so the container was not changed. On the VPS: docker logs blattwerk"
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
