#!/usr/bin/env bash
# Runs the tests named 20 times side by side. What follows goes to pytest: node ids and flags.
set -euo pipefail
cd "$(dirname "$0")/.."

# pytest-repeat adds its step to the id: test[30] runs as test[30-1-20] to test[30-20-20],
# and pytest finds nothing under test[30]. So an id with a parameter is named once per step.
args=()
for arg in "$@"; do
  if [[ $arg == *::*\] ]]; then
    for step in {1..20}; do args+=("${arg%]}-$step-20]"); done
  else
    args+=("$arg")
  fi
done
exec uv run pytest -n 8 --count 20 -x "${args[@]}"
