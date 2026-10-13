#!/usr/bin/env bash
# Does the blattwerk container run the image the canary tried?
#
# Not the ids: a build out of the cache (a commit that changes nothing the image holds) gets a new
# id for the same image, and compose rightly keeps the container. So the check reads what the two
# images hold. The config too: a new `ENV` or `CMD` adds no layer.
# An inspect that fails leaves an empty answer, and an empty answer fails: two empty answers must
# not count as the same.
# The config holds env values and the job log is public: it is never printed.
set -euo pipefail

running=$(docker inspect -f '{{.Image}}' blattwerk) || running=
for part in .RootFS.Layers .Config; do
  runs=$(docker image inspect -f "{{json $part}}" "$running") || runs=
  tried=$(docker image inspect -f "{{json $part}}" blattwerk-blattwerk:canary) || tried=
  if [ -z "$runs" ] || [ "$runs" != "$tried" ]; then
    echo "::error::the blattwerk container does not run the image the canary tried: $part differs or could not be read (the container runs ${running:-nothing})"
    exit 1
  fi
done
echo "the container runs $running, which holds the layers and the config the canary tried"
