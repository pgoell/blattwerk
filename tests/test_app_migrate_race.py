"""Opening the database beside another reader or a crowd of requests moves it once."""

import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from test_app import (
    COUNTED,
    HUGE,
    TABLES,
    dump,
    leftover,
    moved,
    my_id,
    old_database,
    reading,
    sequence,
    user,
    waits,
)
from ui import png

from blattwerk import db


def test_many_requests_move_an_old_database_once(data_dir):
    old_database(data_dir)
    plain = sqlite3.connect(data_dir / "blattwerk.db")
    before = {t: plain.execute(f"SELECT * FROM {t} ORDER BY 1").fetchall() for t in TABLES}
    plain.close()
    with ThreadPoolExecutor(8) as pool:
        cons = list(pool.map(lambda _: db.open_db(), range(8)))
    rows, tables, seq = dump(cons[0])
    assert rows == before
    assert seq == [("sheets", 2), ("templates", 2), ("uploads", 2), ("users", 2)]
    assert not [name for name, _ in tables if name.endswith("_new")]
    for con in cons:
        assert con.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        con.close()


def test_many_requests_start_a_new_database_once(data_dir):
    (data_dir / "users" / "5").mkdir(parents=True)
    with ThreadPoolExecutor(8) as pool:
        cons = list(pool.map(lambda _: db.open_db(), range(8)))
    assert sequence(cons[0]) == [("sheets", 0), ("templates", 0), ("uploads", 0), ("users", 5)]
    for con in cons:
        con.close()


def test_a_second_open_waits_for_the_schema_write(data_dir, monkeypatch):
    """The browser's server and the test open one new file together.

    The schema script takes a write lock. A second open that starts its own write while the first
    still holds one used to raise `database is locked` and fail the test (#342). It waits instead.
    """
    # Shorter than the pause below, so an open that waits on SQLite gives up first.
    monkeypatch.setattr(db, "WAIT", 0.3)
    started = threading.Event()
    release = threading.Event()

    class Holding(sqlite3.Connection):
        def executescript(self, script):
            # The first script holds the write lock, as it does while it creates the tables.
            if not started.is_set():
                self.execute("BEGIN IMMEDIATE")
                started.set()
                assert release.wait(2)
                self.execute("ROLLBACK")
            return super().executescript(script)

    previous = db.sqlite3.connect
    opened = threading.Event()
    seen = threading.Lock()
    arrived = {"n": 0}

    def connect(*args, **more):
        con = previous(*args, factory=Holding, **more)
        with seen:
            arrived["n"] += 1
            if arrived["n"] >= 2:
                opened.set()
        return con

    monkeypatch.setattr(db.sqlite3, "connect", connect)
    errors = []
    done = []

    def open_one():
        try:
            done.append(db.open_db())
        except sqlite3.OperationalError as error:
            errors.append(error)

    first = threading.Thread(target=open_one)
    first.start()
    assert started.wait(2)
    second = threading.Thread(target=open_one)
    second.start()
    # In its own open, and past connecting. Waiting out SQLite would have failed it.
    assert opened.wait(2)
    assert not release.wait(0.5)
    release.set()
    first.join(2)
    second.join(2)
    assert not first.is_alive()
    assert not second.is_alive()
    assert errors == []
    assert len(done) == 2
    for con in done:
        assert db.migrated(con)
        assert con.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        con.close()


def test_old_database_opens_beside_a_read_and_moves_after_it(data_dir, monkeypatch):
    old_database(data_dir)
    reader = reading(data_dir, monkeypatch)
    before = {t: reader.execute(f"SELECT * FROM {t} ORDER BY 1").fetchall() for t in TABLES}
    con = db.open_db()
    waits(con)
    # The old database has no `sqlite_sequence` for `dump` to read.
    for table in TABLES:
        assert [tuple(r) for r in con.execute(f"SELECT * FROM {table} ORDER BY 1")] == before[table]
    con.close()
    reader.close()
    assert db.migrated(db.open_db())
    moved(data_dir, users=2)


def test_new_database_opens_beside_a_read_and_gets_its_counters_after_it(data_dir, monkeypatch):
    # Another request made the tables and has not written the counters yet.
    sqlite3.connect(data_dir / "blattwerk.db").executescript(db.SCHEMA)
    reader = reading(data_dir, monkeypatch)
    con = db.open_db()
    waits(con)
    assert sequence(con) == []
    con.close()
    reader.close()
    assert dict(sequence(db.open_db())) == dict.fromkeys(COUNTED, 0)
    assert my_id(user("a@example.com")) == 1


def test_old_database_waits_for_a_writer_and_moves(data_dir):
    old_database(data_dir)
    writer = sqlite3.connect(data_dir / "blattwerk.db", autocommit=True, check_same_thread=False)
    writer.execute("BEGIN IMMEDIATE")
    # Longer than a second: a move that gave up after one would leave the connection reading.
    timer = threading.Timer(1.2, writer.execute, ["COMMIT"])
    timer.start()
    con = db.open_db()
    timer.join()
    assert db.migrated(con)
    assert con.execute("PRAGMA query_only").fetchone()[0] == 0
    assert con.execute("PRAGMA busy_timeout").fetchone()[0] == 5000
    con.execute("INSERT INTO users (email, password) VALUES ('c@x.de', 'x')")
    assert [r["id"] for r in con.execute("SELECT id FROM users")] == [1, 2, 3]


def test_connection_that_waits_for_the_move_only_reads(data_dir, monkeypatch):
    old_database(data_dir)
    reader = reading(data_dir, monkeypatch)
    con = db.open_db()
    reader.close()
    assert [r["id"] for r in con.execute("SELECT id FROM users")] == [1, 2]
    for write in (
        "INSERT INTO users (email, password) VALUES ('c@x.de', 'x')",
        "INSERT INTO attempts (key) VALUES ('x')",
        "DELETE FROM users",
    ):
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            con.execute(write)
    assert [r["id"] for r in con.execute("SELECT id FROM users")] == [1, 2]
    # A later connection writes again.
    assert my_id(user("c@example.com")) == 3


def test_other_errors_of_the_move_still_raise(data_dir, monkeypatch):
    monkeypatch.setattr(db, "seed", lambda con: con.execute("SELECT * FROM missing"))
    with pytest.raises(sqlite3.OperationalError, match="no such table"):
        db.open_db()


@pytest.mark.parametrize("name", HUGE)
def test_new_database_skips_a_name_too_high_for_an_id(data_dir, name):
    leftover(data_dir, name)
    assert dict(sequence(db.open_db())) == dict.fromkeys(COUNTED, 0)
    client = user("a@example.com")
    assert my_id(client) == 1
    # In the account's own folder too.
    leftover(data_dir, name, owner="1")
    con = db.open_db()
    con.execute("DELETE FROM sqlite_sequence")
    assert dict(sequence(db.open_db())) == {"users": 1, "templates": 0, "sheets": 0, "uploads": 0}
    picture = {"file": ("bild", png(), "image/png")}
    assert client.post("/api/uploads", files=picture).json()["id"] == 1
    assert my_id(user("b@example.com")) == 2


@pytest.mark.parametrize("name", [*HUGE, "0", "08", "٨"])
def test_real_id_beside_a_name_that_is_no_id_still_counts(data_dir, name):
    leftover(data_dir, name)
    leftover(data_dir, "9", owner="7")
    leftover(data_dir, name, owner="7")
    assert dict(sequence(db.open_db())) == {"users": 7, "templates": 0, "sheets": 0, "uploads": 9}
    client = user("a@example.com")
    assert my_id(client) == 8
    picture = {"file": ("bild", png(), "image/png")}
    assert client.post("/api/uploads", files=picture).json()["id"] == 10
