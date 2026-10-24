# Tests of one behaviour each live in the sibling modules. Shared helpers stay here so existing imports keep working.

import sqlite3

from fastapi import FastAPI
from fastapi.testclient import TestClient
from ui import png

from blattwerk import auth, db, sheets, templates, uploads
from blattwerk.app import app

PASSWORD = "richtig-geheim"
MATHS = {"ops": ["+"], "max": 20, "count": 3, "seed": 7}
# The least a sheet's document holds: the server refuses less.
EMPTY = {"pages": [{"blocks": []}], "guides": {"x": [], "y": []}, "grid": 0}


def invite(admin=False):
    return auth.new_link(db.open_db(), admin=admin)


def user(email, admin=False):
    """A client logged in as a new user. https, or the Secure cookie is not sent back."""
    client = TestClient(app, base_url="https://testserver")
    res = client.post(
        "/api/signup", json={"token": invite(admin), "email": email, "password": PASSWORD}
    )
    assert res.status_code == 200
    return client


def own(client):
    """A user's templates, without the built-in ones."""
    return [t for t in client.get("/api/templates").json() if t["id"] > 0]


def my_id(client):
    return client.get("/api/me").json()["id"]


def restarted(client):
    """The same login on a new app on the same file: the process after a deploy."""
    fresh = FastAPI()
    for part in (auth, sheets, templates, uploads):
        fresh.include_router(part.router)
    return TestClient(fresh, base_url="https://testserver", cookies=dict(client.cookies))


def old_database(data_dir, live=False):
    """The database as it was before AUTOINCREMENT, with two users who each own one of each.

    With `live`, as it was after `users` alone had moved.
    """
    old = db.SCHEMA.replace(" AUTOINCREMENT", "")
    assert old != db.SCHEMA
    if live:
        old = old.replace(db.USERS.replace(" AUTOINCREMENT", ""), db.USERS)
        assert old.count("AUTOINCREMENT") == 1
    con = sqlite3.connect(data_dir / "blattwerk.db", autocommit=True)
    con.executescript(old)
    for i in (1, 2):
        con.execute("INSERT INTO users (id, email, password) VALUES (?, ?, 'x')", (i, f"{i}@x.de"))
        con.execute("INSERT INTO sessions VALUES (?, ?, '2999-01-01')", (f"session{i}", i))
        con.execute("INSERT INTO links (token, user_id) VALUES (?, ?)", (f"link{i}", i))
        con.execute("INSERT INTO templates (user_id, name, doc) VALUES (?, 'T', '{}')", (i,))
        con.execute("INSERT INTO sheets (user_id, title, doc) VALUES (?, 'S', '{}')", (i,))
        con.execute("INSERT INTO uploads (user_id, type) VALUES (?, 'image/png')", (i,))
    con.execute("INSERT INTO links (token) VALUES ('invite')")
    con.close()


TABLES = ["users", "sessions", "links", "templates", "sheets", "uploads"]


def dump(con):
    """Every row and every table's definition."""
    rows = {t: [tuple(r) for r in con.execute(f"SELECT * FROM {t} ORDER BY 1")] for t in TABLES}
    names = "name, sql FROM sqlite_master ORDER BY name"
    return rows, [tuple(r) for r in con.execute(f"SELECT {names}")], sequence(con)


def sequence(con):
    return sorted(tuple(r) for r in con.execute("SELECT * FROM sqlite_sequence"))


COUNTED = ["users", "templates", "sheets", "uploads"]


def moved(data_dir, users):
    """Opens an old database and checks the move; `users` is the counter it must end with."""
    plain = sqlite3.connect(data_dir / "blattwerk.db")
    before = {t: plain.execute(f"SELECT * FROM {t} ORDER BY 1").fetchall() for t in TABLES}
    plain.close()

    con = db.open_db()
    rows, tables, seq = after = dump(con)
    assert rows == before
    assert [r["user_id"] for r in con.execute("SELECT user_id FROM uploads")] == [1, 2]
    assert con.execute("PRAGMA foreign_key_check").fetchall() == []
    assert con.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    sql = dict(tables)
    for table in COUNTED:
        assert "AUTOINCREMENT" in sql[table], table
        assert f"{table}_new" not in sql
    for child in TABLES[1:]:
        assert "REFERENCES users (id) ON DELETE CASCADE" in sql[child]
    assert dict(seq) == {"users": users, "templates": 2, "sheets": 2, "uploads": 2}
    assert len(seq) == 4

    # A second start changes nothing.
    assert dump(db.open_db()) == after

    con.execute("DELETE FROM users WHERE id = 1")
    for child in TABLES[1:]:
        owners = [r[0] for r in con.execute(f"SELECT user_id FROM {child} ORDER BY 1")]
        assert owners == ([None, 2] if child == "links" else [2]), child
    assert con.execute("PRAGMA foreign_key_check").fetchall() == []
    client = user("c@example.com")
    assert my_id(client) == users + 1
    # The newest of each is gone with user 2, and its id stays used.
    con.execute("DELETE FROM users WHERE id = 2")
    assert client.post("/api/sheets", json={"title": "x", "doc": EMPTY}).json()["id"] == 3
    assert client.post("/api/templates", json={"name": "x", "doc": EMPTY}).json()["id"] == 3
    picture = {"file": ("bild", png(), "image/png")}
    assert client.post("/api/uploads", files=picture).json()["id"] == 3


def reading(data_dir, monkeypatch):
    """Another connection in the middle of a read: no write can commit beside it."""
    # Short, or each test would wait the whole five seconds.
    monkeypatch.setattr(db, "WAIT", 0.3)
    reader = sqlite3.connect(data_dir / "blattwerk.db", autocommit=True)
    reader.execute("BEGIN")
    reader.execute("SELECT * FROM users").fetchone()
    return reader


def waits(con):
    """The move gave up: the connection reads, and is as any other apart from that."""
    assert not db.migrated(con)
    assert not con.in_transaction
    assert con.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    assert con.execute("PRAGMA query_only").fetchone()[0] == 1
    names = [r[0] for r in con.execute("SELECT name FROM sqlite_master")]
    assert not [name for name in names if name.endswith("_new")]


HUGE = ["99999999999999999999", str(2**63 - 1)]


def leftover(data_dir, name, owner=None):
    """A folder under users/ and a file under uploads/ with a name that is no id."""
    (data_dir / "users" / (owner or name) / "uploads").mkdir(parents=True, exist_ok=True)
    (data_dir / "users" / (owner or name) / "uploads" / name).write_bytes(b"old")


def kinds(page):
    return [b["props"].get("kind", b["type"]) for b in page["blocks"]]
