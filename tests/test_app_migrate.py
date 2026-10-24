"""An old database moves to autoincrement and the counters start above leftover folders."""

import sqlite3

from test_app import (
    COUNTED,
    EMPTY,
    moved,
    my_id,
    old_database,
    sequence,
    user,
)
from ui import png

from blattwerk import db


def test_old_tables_move_to_autoincrement(data_dir):
    old_database(data_dir)
    moved(data_dir, users=2)


def test_tables_beside_a_moved_users_table_move_too(data_dir):
    old_database(data_dir, live=True)
    # Five accounts came and went since `users` moved, and one left its folder.
    plain = sqlite3.connect(data_dir / "blattwerk.db", autocommit=True)
    plain.execute("UPDATE sqlite_sequence SET seq = 7 WHERE name = 'users'")
    plain.close()
    (data_dir / "users" / "5").mkdir(parents=True)
    moved(data_dir, users=7)


def test_counter_starts_above_the_highest_leftover_folder(data_dir):
    old_database(data_dir)
    (data_dir / "users" / "5" / "uploads").mkdir(parents=True)
    (data_dir / "users" / "5" / "uploads" / "9").write_bytes(b"png")
    (data_dir / "users" / "5" / "uploads" / "tmp").write_bytes(b"png")
    (data_dir / "users" / "tmp").mkdir()
    # A digit to str.isdigit, and no number to int.
    (data_dir / "users" / "²").mkdir()
    (data_dir / "users" / "5" / "uploads" / "²").write_bytes(b"png")
    assert dict(sequence(db.open_db())) == {"users": 5, "templates": 2, "sheets": 2, "uploads": 9}
    client = user("c@example.com")
    assert my_id(client) == 6
    picture = {"file": ("bild", png(), "image/png")}
    assert client.post("/api/uploads", files=picture).json()["id"] == 10


def test_new_database_starts_above_the_highest_leftover_folder(data_dir):
    (data_dir / "users" / "5" / "uploads").mkdir(parents=True)
    (data_dir / "users" / "3" / "uploads").mkdir(parents=True)
    (data_dir / "users" / "3" / "uploads" / "9").write_bytes(b"old")
    (data_dir / "users" / "5" / "uploads" / "4").write_bytes(b"old")
    client = user("a@example.com")
    assert my_id(client) == 6
    picture = {"file": ("bild", png(), "image/png")}
    assert client.post("/api/uploads", files=picture).json()["id"] == 10
    assert client.post("/api/sheets", json={"title": "x", "doc": EMPTY}).json()["id"] == 1
    assert client.post("/api/templates", json={"name": "x", "doc": EMPTY}).json()["id"] == 1
    assert (data_dir / "users" / "3" / "uploads" / "9").read_bytes() == b"old"
    assert sorted(p.name for p in (data_dir / "users").iterdir()) == ["3", "5", "6"]


def test_new_database_starts_at_one(data_dir):
    assert dict(sequence(db.open_db())) == dict.fromkeys(COUNTED, 0)
    assert my_id(user("a@example.com")) == 1


def test_new_database_beside_folders_that_are_no_numbers_starts_at_one(data_dir):
    (data_dir / "users" / "tmp" / "uploads").mkdir(parents=True)
    (data_dir / "users" / "tmp" / "uploads" / "x").write_bytes(b"old")
    # A digit to str.isdigit, and no number to int.
    (data_dir / "users" / "²" / "uploads").mkdir(parents=True)
    (data_dir / "users" / "²" / "uploads" / "²").write_bytes(b"old")
    client = user("a@example.com")
    assert my_id(client) == 1
    picture = {"file": ("bild", png(), "image/png")}
    assert client.post("/api/uploads", files=picture).json()["id"] == 1


def test_counter_never_goes_down(data_dir):
    for email in ("a@example.com", "b@example.com", "c@example.com"):
        client = user(email)
    picture = {"file": ("bild", png(), "image/png")}
    assert [client.post("/api/uploads", files=picture).json()["id"] for _ in "ab"] == [1, 2]
    assert client.delete("/api/me").status_code == 200
    # Lower than the counters, and found by a start that looks again.
    (data_dir / "users" / "1" / "uploads").mkdir(parents=True, exist_ok=True)
    (data_dir / "users" / "1" / "uploads" / "1").write_bytes(b"old")
    con = db.open_db()
    before = sequence(con)
    assert dict(before) == {"users": 3, "templates": 0, "sheets": 0, "uploads": 2}
    assert sequence(db.open_db()) == before
    con.execute("BEGIN IMMEDIATE")
    db.seed(con)
    con.execute("COMMIT")
    assert sequence(con) == before
    # A lost row is put back, and no lower than the rows and files that are left.
    con.execute("DELETE FROM sqlite_sequence WHERE name IN ('users', 'uploads')")
    assert dict(sequence(db.open_db())) == {"users": 2, "templates": 0, "sheets": 0, "uploads": 1}


def test_empty_old_tables_move_too(data_dir):
    sqlite3.connect(data_dir / "blattwerk.db").executescript(
        db.SCHEMA.replace(" AUTOINCREMENT", "")
    )
    assert dict(sequence(db.open_db())) == dict.fromkeys(COUNTED, 0)
    client = user("a@example.com")
    assert my_id(client) == 1
    assert client.post("/api/sheets", json={"title": "x", "doc": EMPTY}).json()["id"] == 1
    assert client.post("/api/templates", json={"name": "x", "doc": EMPTY}).json()["id"] == 1
    picture = {"file": ("bild", png(), "image/png")}
    assert client.post("/api/uploads", files=picture).json()["id"] == 1
