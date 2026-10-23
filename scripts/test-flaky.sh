#!/usr/bin/env bash
# Runs the tests named 20 times side by side. What follows goes to pytest: node ids and flags.
set -euo pipefail
cd "$(dirname "$0")/.."

# pytest escapes a non-ascii parameter, so ä is \xe4 in the id it prints with -q.
# The name as typed then matches nothing. Escape that name the same way. An id
# copied from -q is already ascii, and escaping it again would match nothing too.
rewritten=$(
  uv run python - "$@" <<'PY'
import sys

for arg in sys.argv[1:]:
    if not arg.isascii() and "[" in arg:
        base, sep, rest = arg.partition("[")
        arg = base + sep + rest.encode("unicode_escape").decode("ascii")
    sys.stdout.write(arg + "\n")
PY
)

# pytest-repeat adds its step to the id: test[30] runs as test[30-1-20] to test[30-20-20],
# and pytest finds nothing under test[30]. So an id with a parameter is named once per step.
args=()
if [[ -n ${rewritten} ]]; then
  while IFS= read -r arg; do
    if [[ ${arg} == *::*\] ]]; then
      for step in {1..20}; do args+=("${arg%]}-$step-20]"); done
    else
      args+=("$arg")
    fi
  done <<< "${rewritten}"
fi
exec uv run pytest -n 8 --count 20 -x "${args[@]}"
