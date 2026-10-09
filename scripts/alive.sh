#!/usr/bin/env bash
# One try: does the app in the container <name> answer, with its database?
#   alive.sh <container>
set -euo pipefail

# /api/me says 401 only after it has read the tables sessions and users; a dead database says 500
# or 503, and `/` would say 200 without it. No output: the app's logs and errors hold invite
# tokens and the job logs are public. One line, so a log of the call stays one line.
docker exec "$1" /app/.venv/bin/python -c \
  "import http.client, sys; c = http.client.HTTPConnection('127.0.0.1', 8000, timeout=2); c.request('GET', '/api/me'); sys.exit(c.getresponse().status != 401)" 2>/dev/null
