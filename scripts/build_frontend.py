"""Build the frontend. One writer: vite empties ``static/`` before it writes (#256)."""

import fcntl
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "src/blattwerk/.build.lock"


def main():
    os.chdir(ROOT)
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    # Held open until this process exits, which is after npm does. vite removes
    # static/; the lock file lives beside that directory, so the empty does not drop it.
    fd = os.open(LOCK, os.O_CREAT | os.O_RDWR, 0o644)
    fcntl.flock(fd, fcntl.LOCK_EX)
    raise SystemExit(subprocess.call(["npm", "run", "build", "--prefix", "frontend"]))


if __name__ == "__main__":
    main()
