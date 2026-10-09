"""SQLite file on the data volume."""

import logging
import os
import re
import sqlite3
from collections.abc import Iterator
from pathlib import Path
from typing import Annotated

from fastapi import Depends, HTTPException

DATA_DIR = Path(os.environ.get("BLATTWERK_DATA_DIR", "data"))
log = logging.getLogger(__name__)
# Seconds a connection waits for another one's lock.
WAIT = 5
# An id as the app writes it in a folder's or a file's name.
ID = re.compile("[1-9][0-9]*")

# A link with no user is an invite; a link with a user resets that user's password.
# An attempt is one login try, keyed by email or IP.
# AUTOINCREMENT, so a deleted row's id never goes to a later one: a folder is named after its
# account, and a browser may keep an upload under its address for good.
USERS = """(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    admin INTEGER NOT NULL DEFAULT 0,
    created TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
)"""
TEMPLATES = """(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    doc TEXT NOT NULL
)"""
SHEETS = """(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    doc TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    updated TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
)"""
UPLOADS = """(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    type TEXT NOT NULL
)"""
COUNTED = {"users": USERS, "templates": TEMPLATES, "sheets": SHEETS, "uploads": UPLOADS}
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
CREATE TABLE IF NOT EXISTS templates {TEMPLATES};
CREATE TABLE IF NOT EXISTS sheets {SHEETS};
CREATE TABLE IF NOT EXISTS uploads {UPLOADS};
CREATE TABLE IF NOT EXISTS attempts (
    key TEXT NOT NULL,
    created TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
-- The folder of a deleted account that would not go. No REFERENCES: its user is gone.
CREATE TABLE IF NOT EXISTS leftovers (
    user_id INTEGER PRIMARY KEY,
    since TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    error TEXT NOT NULL
);
"""


def open_db() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    # FastAPI may set up and tear down a dependency on different threads.
    con = sqlite3.connect(
        DATA_DIR / "blattwerk.db", timeout=WAIT, autocommit=True, check_same_thread=False
    )
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    if not migrated(con):
        try:
            migrate(con)
        except sqlite3.OperationalError as error:
            if error.sqlite_errorcode != sqlite3.SQLITE_BUSY:
                raise
            # Another connection kept its read or its write open for the whole wait. The request
            # goes on, and a later one moves the tables. Until then no INSERT may take an id: a
            # table from before AUTOINCREMENT or one without its counter would hand out a deleted
            # row's id again.
            log.warning("Database is busy: the move to AUTOINCREMENT waits, this request reads")
            con.execute("PRAGMA query_only = ON")
    return con


def old(con: sqlite3.Connection) -> list[str]:
    """The tables from before AUTOINCREMENT."""
    tables = dict(con.execute("SELECT name, sql FROM sqlite_master").fetchall())
    return [name for name in COUNTED if "AUTOINCREMENT" not in tables[name]]


def migrated(con: sqlite3.Connection) -> bool:
    # An old database may have no `sqlite_sequence` at all, so this reads the tables first.
    # A new one has it empty: SQLite writes a counter with the table's first row.
    names = "name IN ('users', 'templates', 'sheets', 'uploads')"
    counters = f"SELECT count(*) FROM sqlite_sequence WHERE {names}"
    return not old(con) and con.execute(counters).fetchone()[0] == len(COUNTED)


def migrate(con: sqlite3.Connection) -> None:
    """Rebuilds the tables from before AUTOINCREMENT, and gives each of the four its counter.

    Every row keeps its id.
    """
    # Off, or the DROP would cascade into every user's rows. It only takes outside a transaction.
    con.execute("PRAGMA foreign_keys = OFF")
    try:
        con.execute("BEGIN IMMEDIATE")
        try:
            # Another request may have done it while this one waited for the lock.
            if not migrated(con):
                # A table that has its counter stays: the DROP would throw the counter away.
                for name in old(con):
                    con.execute(f"CREATE TABLE {name}_new {COUNTED[name]}")
                    con.execute(f"INSERT INTO {name}_new SELECT * FROM {name}")
                    # The old table goes before the rename: renaming it away would take the
                    # other tables' REFERENCES along.
                    con.execute(f"DROP TABLE {name}")
                    con.execute(f"ALTER TABLE {name}_new RENAME TO {name}")
                seed(con)
            con.execute("COMMIT")
        except BaseException:
            con.execute("ROLLBACK")
            raise
    finally:
        con.execute("PRAGMA foreign_keys = ON")


def seed(con: sqlite3.Connection) -> None:
    """Sets each counter to the highest id in use. A counter never goes down.

    Under the write lock: `sqlite_sequence` lets two rows carry one name.
    """
    users = DATA_DIR / "users"
    # A folder or a picture that a failed delete or an older database left behind keeps its id
    # used.
    left = {"users": users.glob("*"), "uploads": users.glob("*/uploads/*")}
    for name in COUNTED:
        # Only a name the app could have given: any other number may be too high for a counter.
        used = [int(p.name) for p in left.get(name, ()) if ID.fullmatch(p.name)]
        used = [i for i in used if i < 2**63 - 1]
        used += [con.execute(f"SELECT max(id) FROM {name}").fetchone()[0] or 0]
        counter = "SELECT max(seq) FROM sqlite_sequence WHERE name = ?"
        used += [con.execute(counter, (name,)).fetchone()[0] or 0]
        con.execute("DELETE FROM sqlite_sequence WHERE name = ?", (name,))
        con.execute("INSERT INTO sqlite_sequence VALUES (?, ?)", (name, max(used)))


def connect() -> Iterator[sqlite3.Connection]:
    try:
        con = open_db()
    except sqlite3.OperationalError as error:
        if error.sqlite_errorcode != sqlite3.SQLITE_BUSY:
            raise
        # A new file's tables could not be made: another connection kept the file for the whole
        # wait. Nothing is lost, and the next request makes them.
        raise HTTPException(503, headers={"Retry-After": "1"}) from None
    try:
        yield con
    finally:
        con.close()


Con = Annotated[sqlite3.Connection, Depends(connect)]
