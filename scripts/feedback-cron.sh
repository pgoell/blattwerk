#!/bin/bash
# The daily feedback job. Cron entry point:
#   15 5 * * * /path/to/blattwerk/scripts/feedback-cron.sh >> ~/.local/share/blattwerk-feedback/cron.log 2>&1
# Arguments go on to feedback_triage.py (--dry-run, say).
set -euo pipefail

# Cron has a minimal PATH; claude lives in ~/.local/bin.
export PATH="$PATH:$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"
REPO="$(cd "$(dirname "$0")/.." && pwd)"

# Sessions build branches in this checkout. The job reads private data and may write to GitHub,
# so it runs the code as origin/master has it, never a half-built branch.
CODE="$(mktemp -d)"
trap 'rm -rf "$CODE"' EXIT
git -C "$REPO" fetch -q origin master || echo "fetch failed, running the origin/master of the last fetch"
git -C "$REPO" archive origin/master scripts/feedback_triage.py scripts/feedback_privacy.py | tar -x -C "$CODE"

echo "== $(date -Is) feedback job at $(git -C "$REPO" rev-parse --short origin/master)"
python3 "$CODE/scripts/feedback_triage.py" "$@"
