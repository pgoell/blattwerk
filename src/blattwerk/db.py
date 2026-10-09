"""SQLite file on the data volume."""

import os
import sqlite3
from collections.abc import Iterator
from pathlib import Path
from typing import Annotated

from fastapi import Depends

DATA_DIR = Path(os.environ.get("BLATTWERK_DATA_DIR", "data"))

# A link with no user is an invite; a link with a user resets that user's password.
# An attempt is one login try, keyed by email or IP.
# AUTOINCREMENT, so a deleted account's id never goes to a later one.
USERS = """(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    admin INTEGER NOT NULL DEFAULT 0,
    created TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
)"""
SCHEMA = f"""
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS users {USERS};
CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    expires TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS links (
    token TEXT PRIMARY KEY,
    user_id INTEGER REFERENCES users (id) ON DELETE CASCADE,
    admin INTEGER NOT NULL DEFAULT 0,
    created TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS templates (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    doc TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sheets (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    doc TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    updated TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS uploads (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    type TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS attempts (
    key TEXT NOT NULL,
    created TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def open_db() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    # FastAPI may set up and tear down a dependency on different threads.
    con = sqlite3.connect(DATA_DIR / "blattwerk.db", autocommit=True, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    if not migrated(con):
        migrate(con)
    return con


def migrated(con: sqlite3.Connection) -> bool:
    sql = con.execute("SELECT sql FROM sqlite_master WHERE name = 'users'").fetchone()[0]
    return "AUTOINCREMENT" in sql


def migrate(con: sqlite3.Connection) -> None:
    """Rebuilds a `users` table from before AUTOINCREMENT. Every row keeps its id."""
    # Off, or the DROP would cascade into every user's rows. It only takes outside a transaction.
    con.execute("PRAGMA foreign_keys = OFF")
    try:
        con.execute("BEGIN IMMEDIATE")
        try:
            # Another request may have done it while this one waited for the lock.
            if not migrated(con):
                con.execute(f"CREATE TABLE users_new {USERS}")
                con.execute("INSERT INTO users_new SELECT * FROM users")
                # The old table goes before the rename: renaming it away would take the
                # other tables' REFERENCES along.
                con.execute("DROP TABLE users")
                con.execute("ALTER TABLE users_new RENAME TO users")
                # A folder that a failed delete left behind keeps its id used.
                used = [int(p.name) for p in (DATA_DIR / "users").glob("*") if p.name.isdecimal()]
                used += [con.execute("SELECT max(id) FROM users").fetchone()[0] or 0]
                con.execute("DELETE FROM sqlite_sequence WHERE name = 'users'")
                con.execute("INSERT INTO sqlite_sequence VALUES ('users', ?)", (max(used),))
            con.execute("COMMIT")
        except BaseException:
            con.execute("ROLLBACK")
            raise
    finally:
        con.execute("PRAGMA foreign_keys = ON")


def connect() -> Iterator[sqlite3.Connection]:
    con = open_db()
    try:
        yield con
    finally:
        con.close()


Con = Annotated[sqlite3.Connection, Depends(connect)]
