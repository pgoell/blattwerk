#!/usr/bin/env bash
# Runs the browser tests in WebKit. What follows goes to pytest: node ids, -n 0 -x.
set -euo pipefail
cd "$(dirname "$0")/.."
export BROWSER=webkit

# WebKit needs GTK 4 and more. CI and a laptop have them once
# `uv run playwright install --with-deps webkit` has run.
if ldconfig -p | grep -q libgtk-4.so.1; then
  exec uv run pytest "$@"
fi

# A host without them, and without sudo, runs Playwright's own image. It keeps a venv of its own
# under ~/.cache/blattwerk-webkit. After a change to uv.lock: rm -rf ~/.cache/blattwerk-webkit/venv.
cache="$HOME/.cache/blattwerk-webkit"
mkdir -p "$cache"
exec docker run --rm --init --ipc=host --user "$(id -u):$(id -g)" \
  -e BROWSER -e SHARD -e HOME=/cache -e UV_PROJECT_ENVIRONMENT=/cache/venv -e UV_CACHE_DIR=/cache/uv \
  -v "$cache":/cache -v "$(command -v uv)":/usr/local/bin/uv:ro -v "$PWD":/work -w /work \
  mcr.microsoft.com/playwright:v1.63.0-noble \
  sh -c 'test -x /cache/venv/bin/python || uv sync -q; exec uv run --no-sync pytest "$@"' sh "$@"
