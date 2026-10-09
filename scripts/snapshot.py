"""A copy of the database as it is before a deploy.

    python3 scripts/snapshot.py <database> <folder> <sha>

Writes <folder>/pre-<sha>.db and keeps the newest 30 of those. Standard library only: the deploy
runs it with the runner's own python3, which has no venv.
"""

import argparse
import os
import sqlite3
import sys
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("source", type=Path)
parser.add_argument("folder", type=Path)
parser.add_argument("sha")
parser.add_argument("--keep", type=int, default=30)
parser.add_argument("--timeout", type=float, default=30)
args = parser.parse_args()

if not args.source.exists():
    print(f"no database at {args.source}, nothing to snapshot")
    sys.exit(0)


def rows(con: sqlite3.Connection) -> dict[str, int]:
    tables = "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
    names = [name for (name,) in con.execute(tables)]
    return {name: con.execute(f'SELECT count(*) FROM "{name}"').fetchone()[0] for name in names}


args.folder.mkdir(parents=True, exist_ok=True)
# Not named pre-*.db: a half-written copy must never pass for a snapshot.
tmp = args.folder / f".pre-{args.sha}.db.tmp"
journal = args.folder / f"{tmp.name}-journal"
try:
    tmp.unlink(missing_ok=True)
    journal.unlink(missing_ok=True)
    # Made here, so the copy is never readable by others. SQLite keeps the mode.
    os.close(os.open(tmp, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600))
    uri = f"{args.source.resolve().as_uri()}?mode=ro"
    src = sqlite3.connect(uri, uri=True, timeout=args.timeout, isolation_level=None)
    dst = sqlite3.connect(tmp)
    try:
        # The count takes the read lock, and waits for a writer no longer than the timeout.
        # backup() alone would wait for ever. One transaction, so the copy must hold the same rows.
        src.execute("BEGIN")
        before = rows(src)
        src.backup(dst)
        src.execute("COMMIT")
        check = dst.execute("PRAGMA integrity_check").fetchone()[0]
        after = rows(dst)
    finally:
        src.close()
        dst.close()
    if check != "ok":
        raise RuntimeError(f"integrity_check of the copy: {check}")
    if after != before:
        raise RuntimeError(f"the copy holds {after}, the database {before}")
    # A rerun for the same commit may come after the new code moved the schema. The first file
    # is the state before that code, so it stays.
    final, n = args.folder / f"pre-{args.sha}.db", 1
    while final.exists():
        n += 1
        final = args.folder / f"pre-{args.sha}-{n}.db"
    os.replace(tmp, final)
except Exception as error:
    tmp.unlink(missing_ok=True)
    journal.unlink(missing_ok=True)
    print(f"snapshot failed: {error}", file=sys.stderr)
    if "readonly" in str(error):
        # The app died in the middle of a write and left its journal. Only a writer can mend that.
        print("Open the site once, so the app mends the database, then rerun.", file=sys.stderr)
    sys.exit(1)

print(final, *(f"{name}={count}" for name, count in after.items()))
# Never the one just written, whatever the clock says of the others.
snapshots = [p for p in args.folder.glob("pre-*.db") if p.is_file() and p != final]
others = max(args.keep - 1, 0)
for old in sorted(snapshots, key=lambda p: p.stat().st_mtime, reverse=True)[others:]:
    old.unlink()
    print(f"deleted {old}")
