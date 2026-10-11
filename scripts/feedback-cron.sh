#!/bin/bash
# The daily feedback job. Sessions build branches in this checkout, and the job reads private
# data and may write to GitHub. So cron runs this file and the Python as origin/master has them,
# never as the checkout stands:
#   15 5 * * * cd /path/to/blattwerk && (git show origin/master:scripts/feedback-cron.sh | bash) >> ~/.local/share/blattwerk-feedback/cron.log 2>&1
# By hand, from the repo: git show origin/master:scripts/feedback-cron.sh | bash -s -- --dry-run
# Arguments go on to feedback_triage.py.
set -euo pipefail

# Cron has a minimal PATH; claude lives in ~/.local/bin.
export PATH="$PATH:$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"
# The folder cron stands in, not this file's place: the file comes down a pipe.
REPO="$(git rev-parse --show-toplevel)"

CODE="$(mktemp -d)"
trap 'rm -rf "$CODE"' EXIT
# A fetch that hangs or asks for a password must not hold tomorrow's run.
GIT_TERMINAL_PROMPT=0 timeout 120 git -C "$REPO" fetch -q origin master \
  || echo "fetch failed, running the origin/master of the last fetch"
git -C "$REPO" archive origin/master scripts/feedback_triage.py scripts/feedback_privacy.py | tar -x -C "$CODE"

echo "== $(date -Is) feedback job at $(git -C "$REPO" rev-parse --short origin/master)"
python3 "$CODE/scripts/feedback_triage.py" "$@"
