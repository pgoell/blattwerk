#!/usr/bin/env bash
# Runs the browser tests in WebKit. What follows goes to pytest: node ids, -n 0 -x.
set -euo pipefail
cd "$(dirname "$0")/.."
export BLATTWERK_BROWSER=webkit

# WebKit needs GTK 4 and more. CI and a laptop have them once
# `uv run playwright install --with-deps webkit` has run. No pipe into `grep -q`: it stops at the
# first match, ldconfig's next write then gets SIGPIPE, and pipefail took that for "no GTK", so 5
# of 133 WebKit shards in CI looked for docker (exit 127). A host without docker has no other way.
if ! command -v docker >/dev/null || [[ "$(ldconfig -p)" == *libgtk-4.so.1* ]]; then
  exec uv run pytest "$@"
fi

# A host without them, and without sudo, runs Playwright's own image. It keeps a venv of its own
# under ~/.cache/blattwerk-webkit, synced to uv.lock on each run: a venv left on an older Playwright
# looks for browsers the image no longer has.
cache="$HOME/.cache/blattwerk-webkit"
mkdir -p "$cache"
exec docker run --rm --init --ipc=host --user "$(id -u):$(id -g)" \
  -e BLATTWERK_BROWSER -e SHARD -e HOME=/cache -e UV_PROJECT_ENVIRONMENT=/cache/venv -e UV_CACHE_DIR=/cache/uv \
  -v "$cache":/cache -v "$(command -v uv)":/usr/local/bin/uv:ro -v "$PWD":/work -w /work \
  mcr.microsoft.com/playwright:v1.64.0-noble \
  sh -c 'uv sync -q; exec uv run --no-sync pytest "$@"' sh "$@"
