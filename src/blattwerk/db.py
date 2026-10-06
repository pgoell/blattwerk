"""SQLite file on the data volume."""

import os
import sqlite3
from collections.abc import Iterator
from pathlib import Path
from typing import Annotated

from fastapi import Depends

DATA_DIR = Path(os.environ.get("BLATTWERK_DATA_DIR", "data"))

# A link with no user is an invite; a link with a user resets that user's password.
SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    admin INTEGER NOT NULL DEFAULT 0,
    created TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
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
"""


def open_db() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    # FastAPI may set up and tear down a dependency on different threads.
    con = sqlite3.connect(DATA_DIR / "blattwerk.db", autocommit=True, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con


def connect() -> Iterator[sqlite3.Connection]:
    con = open_db()
    try:
        yield con
    finally:
        con.close()


Con = Annotated[sqlite3.Connection, Depends(connect)]
