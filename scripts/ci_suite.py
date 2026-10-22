"""Whether a pull request runs the browser suite.

A push to master always runs it: the workflow decides that before calling this.
A pull request skips the suite only when every changed file sits under docs/
or .cursor/skills/. An empty diff runs the suite.

Reads paths on stdin, one per line. Exits 0 when the suite runs, 1 when it does not.
"""

import sys

SKIP_PREFIXES = ("docs/", ".cursor/skills/")


def suite_runs(files):
    """True when this diff has to run the sharded suite."""
    paths = [path for path in files if path]
    if not paths:
        return True
    return any(not path.startswith(SKIP_PREFIXES) for path in paths)


def main():
    files = [line.strip() for line in sys.stdin.read().splitlines()]
    sys.exit(0 if suite_runs(files) else 1)


if __name__ == "__main__":
    main()
