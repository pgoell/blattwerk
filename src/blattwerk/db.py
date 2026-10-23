"""SQLite file on the data volume."""

import logging
import os
import re
import sqlite3
import threading
from collections.abc import Iterator
from pathlib import Path
from typing import Annotated

from fastapi import Depends, HTTPException
from pydantic import AfterValidator, Field

DATA_DIR = Path(os.environ.get("BLATTWERK_DATA_DIR", "data"))
log = logging.getLogger(__name__)
# Seconds a connection waits for another one's lock.
WAIT = 5
# One schema script at a time. A test and the browser's server open one new file in one
# process, and both used to run this script. It needs the write lock, and the open that
# lost it raised "database is locked" (#342).
schema_lock = threading.Lock()
# An id as the app writes it in a folder's or a file's name.
ID = re.compile("[1-9][0-9]*")

# A link with no user is an invite; a link with a user resets that user's password.
# An attempt is one login try, keyed by email or IP.
# AUTOINCREMENT, so a deleted row's id never goes to a later one: a folder is named after its
# account, and a browser may keep an upload under its address for good.
# plan, paid_until and renewal are the account's plan. A database from before them gains the
# columns in ensure_plan: CREATE TABLE IF NOT EXISTS does not add a column.
USERS = """(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    admin INTEGER NOT NULL DEFAULT 0,
    created TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    plan TEXT NOT NULL DEFAULT 'free',
    paid_until TEXT,
    renewal TEXT NOT NULL DEFAULT 'none'
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
CREATE TABLE IF NOT EXISTS tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    hash TEXT NOT NULL,
    name TEXT NOT NULL,
    created TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_used TEXT
);
CREATE TABLE IF NOT EXISTS templates {TEMPLATES};
CREATE TABLE IF NOT EXISTS sheets {SHEETS};
CREATE TABLE IF NOT EXISTS uploads {UPLOADS};
-- A link to a frozen copy of one sheet. The token is the link. Deleting the sheet or the
-- account deletes the row, and the link dies with it.
CREATE TABLE IF NOT EXISTS shares (
    token TEXT PRIMARY KEY,
    sheet_id INTEGER NOT NULL UNIQUE REFERENCES sheets (id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    doc TEXT NOT NULL,
    updated TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS shares_user ON shares (user_id);
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
-- A program that registered itself (RFC 7591). Public: it has no secret.
CREATE TABLE IF NOT EXISTS oauth_clients (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    redirect_uris TEXT NOT NULL,
    created TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
-- An authorization code, by its hash. Deleted when it is used.
CREATE TABLE IF NOT EXISTS oauth_codes (
    hash TEXT PRIMARY KEY,
    client_id TEXT NOT NULL REFERENCES oauth_clients (id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    redirect_uri TEXT NOT NULL,
    challenge TEXT NOT NULL,
    resource TEXT NOT NULL,
    expires TEXT NOT NULL
);
-- A connected program: one teacher's yes to one client, with its current tokens' hashes.
CREATE TABLE IF NOT EXISTS oauth_grants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    client_id TEXT NOT NULL REFERENCES oauth_clients (id) ON DELETE CASCADE,
    code TEXT NOT NULL,
    access_hash TEXT NOT NULL,
    access_expires TEXT NOT NULL,
    refresh_hash TEXT NOT NULL,
    refresh_expires TEXT NOT NULL,
    resource TEXT NOT NULL,
    created TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_used TEXT
);
-- A provider event, once. The same id again does not move the plan a second time.
CREATE TABLE IF NOT EXISTS billing_events (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    type TEXT NOT NULL,
    paid_until TEXT,
    created TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
-- One school, the teachers who have a seat there, and the copies in its folder. A seat is one
-- school per teacher. The folder keeps the author's name after the account is gone.
CREATE TABLE IF NOT EXISTS schools (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    created TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS seats (
    user_id INTEGER PRIMARY KEY REFERENCES users (id) ON DELETE CASCADE,
    school_id INTEGER NOT NULL REFERENCES schools (id) ON DELETE CASCADE,
    admin INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS folder_sheets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    school_id INTEGER NOT NULL REFERENCES schools (id) ON DELETE CASCADE,
    author_id INTEGER REFERENCES users (id) ON DELETE SET NULL,
    author_name TEXT NOT NULL,
    title TEXT NOT NULL,
    label TEXT NOT NULL DEFAULT '',
    doc TEXT NOT NULL,
    created TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS folder_files (
    entry_id INTEGER NOT NULL REFERENCES folder_sheets (id) ON DELETE CASCADE,
    upload_id INTEGER NOT NULL,
    type TEXT NOT NULL,
    PRIMARY KEY (entry_id, upload_id)
);
CREATE INDEX IF NOT EXISTS seats_school ON seats (school_id);
CREATE INDEX IF NOT EXISTS folder_sheets_school ON folder_sheets (school_id);
CREATE INDEX IF NOT EXISTS folder_files_upload ON folder_files (upload_id);
"""

# Every table the script creates. Read from the script, so a new table is made on the next open.
CREATED = tuple(re.findall(r"CREATE TABLE IF NOT EXISTS (\w+)", SCHEMA))


def schema_ready(con: sqlite3.Connection) -> bool:
    """The script has nothing left to write. A read, so a writer of the schema is left alone."""
    try:
        names = con.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        found = {name for (name,) in names}
        # A table may be here and still want its counter, or be missing `sqlite_sequence` entirely.
        return all(name in found for name in CREATED) and migrated(con)
    except sqlite3.OperationalError as error:
        if error.sqlite_errorcode != sqlite3.SQLITE_BUSY:
            raise
        # A writer holds the file. The caller takes the schema lock and looks again.
        return False


def open_db() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    # FastAPI may set up and tear down a dependency on different threads.
    con = sqlite3.connect(
        DATA_DIR / "blattwerk.db", timeout=WAIT, autocommit=True, check_same_thread=False
    )
    con.row_factory = sqlite3.Row
    # Per connection. The script is not run again once the tables are there, and it was what
    # turned this on.
    con.execute("PRAGMA foreign_keys = ON")
    # The plan columns are not a new table, so a database that already has every table still
    # needs them. They go on before the move: the copy reads every column of the old table.
    if not schema_ready(con) or not plan_ready(con):
        with schema_lock:
            # The open that held the lock may have finished the script while this one waited.
            if not schema_ready(con):
                con.executescript(SCHEMA)
            if not plan_ready(con):
                try:
                    ensure_plan(con)
                except sqlite3.OperationalError as error:
                    if error.sqlite_errorcode != sqlite3.SQLITE_BUSY:
                        raise
                    # Another connection kept the file for the whole wait. The request can read;
                    # a later one adds the columns. Until then a row from before the columns is
                    # read as a free account.
                    log.warning("Database is busy: the plan columns wait, this request reads")
                    con.execute("PRAGMA query_only = ON")
                    return con
            if not migrated(con):
                try:
                    migrate(con)
                except sqlite3.OperationalError as error:
                    if error.sqlite_errorcode != sqlite3.SQLITE_BUSY:
                        raise
                    # Another connection kept its read or its write open for the whole wait.
                    # The request goes on, and a later one moves the tables. Until then no
                    # INSERT may take an id: a table from before AUTOINCREMENT or one without
                    # its counter would hand out a deleted row's id again.
                    log.warning(
                        "Database is busy: the move to AUTOINCREMENT waits, this request reads"
                    )
                    con.execute("PRAGMA query_only = ON")
    return con


# Added to `users` for a database that already exists. The default fills the rows already there.
PLAN_COLUMNS = (
    ("plan", "TEXT NOT NULL DEFAULT 'free'"),
    ("paid_until", "TEXT"),
    ("renewal", "TEXT NOT NULL DEFAULT 'none'"),
)


def plan_ready(con: sqlite3.Connection) -> bool:
    """The account table already has the plan columns. A read, so a writer is left alone."""
    try:
        have = {row["name"] for row in con.execute("PRAGMA table_info(users)")}
    except sqlite3.OperationalError as error:
        if error.sqlite_errorcode != sqlite3.SQLITE_BUSY:
            raise
        return False
    return all(name in have for name, _ in PLAN_COLUMNS)


def ensure_plan(con: sqlite3.Connection) -> None:
    """Adds the plan columns to a database from before them."""
    have = {row["name"] for row in con.execute("PRAGMA table_info(users)")}
    for name, decl in PLAN_COLUMNS:
        if name not in have:
            con.execute(f"ALTER TABLE users ADD COLUMN {name} {decl}")


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

# SQLite's whole numbers have 64 bits, and a query that brings a larger one fails. One in a body
# is refused with it.
Whole = Annotated[int, Field(ge=-(2**63), lt=2**63)]


def held(number: int) -> int:
    # No row has an id that SQLite cannot hold: it is as missing as one that never was.
    if not -(2**63) <= number < 2**63:
        raise HTTPException(404)
    return number


# An id in an address.
Id = Annotated[int, AfterValidator(held)]
