import json
import os
import re
import sqlite3
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI
from fastapi.testclient import TestClient

from blattwerk import auth, db, sheets, templates, uploads
from blattwerk.app import app

PASSWORD = "richtig-geheim"
MATHS = {"ops": ["+"], "max": 20, "count": 3, "seed": 7}


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


def test_logged_out_gets_401():
    client = TestClient(app, base_url="https://testserver")
    assert client.get("/api/me").status_code == 401
    assert client.post("/api/feedback", data={"text": "x"}).status_code == 401
    assert client.get("/api/admin/users").status_code == 401
    assert client.get("/api/templates").status_code == 401
    assert client.post("/api/templates", json={"name": "x", "doc": {}}).status_code == 401
    assert client.delete("/api/templates/1").status_code == 401
    assert client.get("/api/sheets").status_code == 401
    assert client.post("/api/sheets", json={"title": "x", "doc": {}}).status_code == 401
    assert client.get("/api/sheets/1").status_code == 401
    assert client.patch("/api/sheets/1", json={"title": "x"}).status_code == 401
    assert client.post("/api/sheets/1/duplicate").status_code == 401
    assert client.delete("/api/sheets/1").status_code == 401
    assert client.get("/api/sheets/1/pdf").status_code == 401
    assert client.post("/api/maths", json=MATHS).status_code == 401


def test_invite_works_once():
    token = invite()
    client = TestClient(app, base_url="https://testserver")
    body = {"token": token, "email": "a@example.com", "password": PASSWORD}
    assert client.post("/api/signup", json=body).json()["email"] == "a@example.com"
    assert client.post("/api/signup", json={**body, "email": "b@example.com"}).status_code == 404


def test_taken_email_keeps_the_invite():
    user("a@example.com")
    token = invite()
    client = TestClient(app, base_url="https://testserver")
    body = {"token": token, "email": "A@example.com", "password": PASSWORD}
    assert client.post("/api/signup", json=body).status_code == 409
    assert client.post("/api/signup", json={**body, "email": "b@example.com"}).status_code == 200


def test_old_invite_is_dead():
    token = invite()
    db.open_db().execute("UPDATE links SET created = datetime('now', '-8 days')")
    client = TestClient(app, base_url="https://testserver")
    body = {"token": token, "email": "a@example.com", "password": PASSWORD}
    assert client.post("/api/signup", json=body).status_code == 404


def test_login_and_logout():
    user("a@example.com")
    client = TestClient(app, base_url="https://testserver")
    wrong = {"email": "a@example.com", "password": "falsch-falsch"}
    assert client.post("/api/login", json=wrong).status_code == 401
    assert client.post("/api/login", json={**wrong, "email": "x@example.com"}).status_code == 401
    assert client.post("/api/login", json={**wrong, "password": PASSWORD}).status_code == 200
    assert client.get("/api/me").json()["email"] == "a@example.com"
    client.post("/api/logout")
    assert client.get("/api/me").status_code == 401


def test_login_is_rate_limited():
    client = TestClient(app, base_url="https://testserver")
    body = {"email": "a@example.com", "password": "falsch-falsch"}
    for _ in range(auth.TRIES):
        assert client.post("/api/login", json=body).status_code == 401
    assert client.post("/api/login", json=body).status_code == 429


def test_rate_limit_survives_a_restart():
    body = {"email": "a@example.com", "password": "falsch-falsch"}
    con = db.open_db()
    for _ in range(auth.TRIES):
        auth.limit(con, "email:a@example.com")
    con.close()
    # A new app on the same file stands in for the process after a deploy.
    fresh = FastAPI()
    fresh.include_router(auth.router)
    client = TestClient(fresh, base_url="https://testserver")
    assert client.post("/api/login", json=body).status_code == 429


def test_old_login_tries_are_dropped():
    client = TestClient(app, base_url="https://testserver")
    body = {"email": "a@example.com", "password": "falsch-falsch"}
    for _ in range(auth.TRIES):
        client.post("/api/login", json=body)
    con = db.open_db()
    con.execute(f"UPDATE attempts SET created = datetime('now', '-{auth.WINDOW} seconds')")
    assert client.post("/api/login", json=body).status_code == 401
    assert con.execute("SELECT count(*) FROM attempts").fetchone()[0] == 2


def test_admin_calls_do_not_exist_for_others():
    teacher = user("a@example.com")
    assert teacher.get("/api/admin/users").status_code == 404
    assert teacher.post("/api/admin/invites").status_code == 404
    assert teacher.post("/api/admin/users/1/reset").status_code == 404


def test_admin_invites_and_resets():
    admin = user("admin@example.com", admin=True)
    teacher = TestClient(app, base_url="https://testserver")
    token = admin.post("/api/admin/invites").json()["token"]
    body = {"token": token, "email": "a@example.com", "password": PASSWORD}
    teacher_id = teacher.post("/api/signup", json=body).json()["id"]
    assert [u["email"] for u in admin.get("/api/admin/users").json()] == [
        "admin@example.com",
        "a@example.com",
    ]

    token = admin.post(f"/api/admin/users/{teacher_id}/reset").json()["token"]
    assert admin.post("/api/admin/users/99/reset").status_code == 404
    # A reset link is no invite.
    assert teacher.post("/api/signup", json={**body, "token": token}).status_code == 404
    fresh = TestClient(app, base_url="https://testserver")
    new = {"token": token, "password": "ganz-neu-geheim"}
    assert fresh.post("/api/reset", json=new).status_code == 200
    assert fresh.post("/api/reset", json=new).status_code == 404
    # The reset ends the old sessions.
    assert teacher.get("/api/me").status_code == 401
    login = {"email": "a@example.com", "password": "ganz-neu-geheim"}
    assert teacher.post("/api/login", json=login).status_code == 200


def test_feedback_lands_in_the_users_folder(data_dir):
    client = user("a@example.com")
    res = client.post(
        "/api/feedback",
        data={"text": "Alles langsam"},
        files=[
            ("audio", ("clip", b"one", "audio/webm;codecs=opus")),
            ("audio", ("clip", b"two", "audio/mp4")),
            ("photo", ("photo", b"page1", "image/jpeg")),
            ("screenshot", ("screenshot", b"screen", "image/jpeg")),
            ("other", ("x", b"ignored", "image/jpeg")),
        ],
    )
    out = data_dir / "users" / "1" / "feedback" / res.json()["saved"]
    assert json.loads((out / "feedback.json").read_text()) == {"text": "Alles langsam"}
    assert (out / "audio-1.webm").read_bytes() == b"one"
    assert (out / "audio-2.m4a").read_bytes() == b"two"
    assert (out / "photo-1.jpg").read_bytes() == b"page1"
    assert (out / "screenshot-1.jpg").read_bytes() == b"screen"
    assert len(list(out.iterdir())) == 5


def test_delete_account_removes_user_and_feedback(data_dir):
    client = user("a@example.com")
    other = user("b@example.com")
    client.post("/api/sheets", json={"title": "Meins", "doc": {}})
    other.post("/api/sheets", json={"title": "Deins", "doc": {}})
    client.post("/api/feedback", data={"text": "x"})
    other.post("/api/feedback", data={"text": "y"})
    assert client.delete("/api/me").status_code == 200
    assert client.get("/api/me").status_code == 401
    assert not (data_dir / "users" / "1").exists()
    assert (data_dir / "users" / "2").exists()
    assert [r["title"] for r in db.open_db().execute("SELECT title FROM sheets")] == ["Deins"]
    login = {"email": "a@example.com", "password": PASSWORD}
    assert client.post("/api/login", json=login).status_code == 401


def own(client):
    """A user's templates, without the built-in ones."""
    return [t for t in client.get("/api/templates").json() if t["id"] > 0]


def my_id(client):
    return client.get("/api/me").json()["id"]


def test_deleted_account_id_is_not_reused():
    user("a@example.com")
    newest = user("b@example.com")
    assert my_id(newest) == 2
    newest.delete("/api/me")
    again = user("c@example.com")
    assert my_id(again) == 3
    again.delete("/api/me")
    # A new app on the same file stands in for the process after a deploy.
    fresh = FastAPI()
    fresh.include_router(auth.router)
    client = TestClient(fresh, base_url="https://testserver")
    body = {"token": invite(), "email": "d@example.com", "password": PASSWORD}
    assert client.post("/api/signup", json=body).json()["id"] == 4


def restarted(client):
    """The same login on a new app on the same file: the process after a deploy."""
    fresh = FastAPI()
    for part in (auth, sheets, templates, uploads):
        fresh.include_router(part.router)
    return TestClient(fresh, base_url="https://testserver", cookies=dict(client.cookies))


def test_deleted_sheet_id_is_not_reused():
    client = user("a@example.com")
    ids = [client.post("/api/sheets", json={"title": "x", "doc": {}}).json()["id"] for _ in "ab"]
    assert ids == [1, 2]
    assert client.delete("/api/sheets/2").status_code == 200
    assert client.post("/api/sheets", json={"title": "x", "doc": {}}).json()["id"] == 3
    assert client.delete("/api/sheets/3").status_code == 200
    again = restarted(client).post("/api/sheets", json={"title": "x", "doc": {}})
    assert again.json()["id"] == 4


def test_deleted_template_id_is_not_reused():
    client = user("a@example.com")
    ids = [client.post("/api/templates", json={"name": "x", "doc": {}}).json()["id"] for _ in "ab"]
    assert ids == [1, 2]
    assert client.delete("/api/templates/2").status_code == 200
    assert client.post("/api/templates", json={"name": "x", "doc": {}}).json()["id"] == 3
    assert client.delete("/api/templates/3").status_code == 200
    again = restarted(client).post("/api/templates", json={"name": "x", "doc": {}})
    assert again.json()["id"] == 4


def test_deleted_upload_id_is_not_reused():
    """No call deletes one upload: its row goes with the account, here by hand."""
    client = user("a@example.com")
    picture = {"file": ("bild", b"png", "image/png")}
    assert [client.post("/api/uploads", files=picture).json()["id"] for _ in "ab"] == [1, 2]
    con = db.open_db()
    con.execute("DELETE FROM uploads WHERE id = 2")
    assert client.post("/api/uploads", files=picture).json()["id"] == 3
    con.execute("DELETE FROM uploads WHERE id = 3")
    assert restarted(client).post("/api/uploads", files=picture).json()["id"] == 4


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
    assert client.post("/api/sheets", json={"title": "x", "doc": {}}).json()["id"] == 3
    assert client.post("/api/templates", json={"name": "x", "doc": {}}).json()["id"] == 3
    picture = {"file": ("bild", b"png", "image/png")}
    assert client.post("/api/uploads", files=picture).json()["id"] == 3


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
    picture = {"file": ("bild", b"png", "image/png")}
    assert client.post("/api/uploads", files=picture).json()["id"] == 10


def test_new_database_starts_above_the_highest_leftover_folder(data_dir):
    (data_dir / "users" / "5" / "uploads").mkdir(parents=True)
    (data_dir / "users" / "3" / "uploads").mkdir(parents=True)
    (data_dir / "users" / "3" / "uploads" / "9").write_bytes(b"old")
    (data_dir / "users" / "5" / "uploads" / "4").write_bytes(b"old")
    client = user("a@example.com")
    assert my_id(client) == 6
    picture = {"file": ("bild", b"png", "image/png")}
    assert client.post("/api/uploads", files=picture).json()["id"] == 10
    assert client.post("/api/sheets", json={"title": "x", "doc": {}}).json()["id"] == 1
    assert client.post("/api/templates", json={"name": "x", "doc": {}}).json()["id"] == 1
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
    picture = {"file": ("bild", b"png", "image/png")}
    assert client.post("/api/uploads", files=picture).json()["id"] == 1


def test_counter_never_goes_down(data_dir):
    for email in ("a@example.com", "b@example.com", "c@example.com"):
        client = user(email)
    picture = {"file": ("bild", b"png", "image/png")}
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
    assert client.post("/api/sheets", json={"title": "x", "doc": {}}).json()["id"] == 1
    assert client.post("/api/templates", json={"name": "x", "doc": {}}).json()["id"] == 1
    picture = {"file": ("bild", b"png", "image/png")}
    assert client.post("/api/uploads", files=picture).json()["id"] == 1


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


def test_new_account_inherits_nothing_from_a_deleted_one(data_dir):
    a = user("a@example.com")
    a_id = my_id(a)
    a.post("/api/sheets", json={"title": "Meins", "doc": {}})
    a.post("/api/templates", json={"name": "Meins", "doc": {}})
    upload = a.post("/api/uploads", files={"file": ("bild", b"png", "image/png")}).json()["id"]
    a.post("/api/feedback", data={"text": "x"})
    con = db.open_db()
    reset = auth.new_link(con, a_id)
    early = invite()
    cookie = a.cookies["session"]
    assert a.delete("/api/me").status_code == 200

    stale = TestClient(app, base_url="https://testserver", cookies={"session": cookie})
    assert stale.get("/api/me").status_code == 401
    b = user("b@example.com")
    b_id = my_id(b)
    assert b_id != a_id
    assert b.get("/api/sheets").json() == []
    assert own(b) == []
    assert b.get(f"/api/uploads/{upload}").status_code == 404
    assert not (data_dir / "users" / str(b_id)).exists()
    assert not (data_dir / "users" / str(a_id)).exists()
    assert stale.get("/api/me").status_code == 401
    # Nothing of A is left for a later account to own: no row, no session, no link.
    for table in TABLES[1:]:
        count = f"SELECT count(*) FROM {table} WHERE user_id = ?"
        assert con.execute(count, (a_id,)).fetchone()[0] == 0, table
    # A's reset link is dead, and B's password stays B's.
    new = {"token": reset, "password": "ganz-neu-geheim"}
    assert stale.post("/api/reset", json=new).status_code == 404
    login = {"email": "b@example.com", "password": PASSWORD}
    assert stale.post("/api/login", json=login).status_code == 200
    # An invite made before the delete is no one's: it opens a new account, not A's.
    c = TestClient(app, base_url="https://testserver")
    body = {"token": early, "email": "c@example.com", "password": PASSWORD}
    assert c.post("/api/signup", json=body).json()["id"] not in (a_id, b_id)
    assert c.get("/api/sheets").json() == []


def test_leftover_folder_never_reaches_a_later_account(data_dir, monkeypatch):
    a = user("a@example.com")
    a.post("/api/uploads", files={"file": ("bild", b"png", "image/png")})
    a.post("/api/feedback", data={"text": "x"})
    # The delete of the folder fails, as on a full or read-only disk.
    monkeypatch.setattr(auth.shutil, "rmtree", lambda *args, **kwargs: None)
    assert a.delete("/api/me").status_code == 200
    left = data_dir / "users" / "1"
    files = sorted(left.rglob("*"))
    assert len(files) == 5

    b = user("b@example.com")
    assert my_id(b) == 2
    upload = b.post("/api/uploads", files={"file": ("bild", b"png", "image/png")}).json()["id"]
    stamp = b.post("/api/feedback", data={"text": "y"}).json()["saved"]
    assert (data_dir / "users" / "2" / "uploads" / str(upload)).is_file()
    assert (data_dir / "users" / "2" / "feedback" / stamp).is_dir()
    assert sorted(left.rglob("*")) == files


def test_deleting_an_account_ends_every_session_and_open_link():
    first = user("a@example.com")
    second = TestClient(app, base_url="https://testserver")
    login = {"email": "a@example.com", "password": PASSWORD}
    assert second.post("/api/login", json=login).status_code == 200
    reset = auth.new_link(db.open_db(), my_id(first))
    assert first.delete("/api/me").status_code == 200
    assert second.get("/api/me").status_code == 401
    assert second.post("/api/sheets", json={"title": "x", "doc": {}}).status_code == 401
    new = {"token": reset, "password": "ganz-neu-geheim"}
    assert second.post("/api/reset", json=new).status_code == 404
    assert db.open_db().execute("SELECT count(*) FROM links").fetchone()[0] == 0


def kinds(page):
    return [b["props"].get("kind", b["type"]) for b in page["blocks"]]


def test_built_in_templates_are_everyones_and_stay():
    client = user("a@example.com")
    other = user("b@example.com")
    built_in = client.get("/api/templates").json()
    assert other.get("/api/templates").json() == built_in
    assert [t["name"] for t in built_in] == ["Arbeitsblatt", "Klassenarbeit", "Beschriftungsblatt"]
    for t in built_in:
        assert client.delete(f"/api/templates/{t['id']}").status_code == 404
    assert client.get("/api/templates").json() == built_in

    for t in built_in:
        blocks = [b for page in t["doc"]["pages"] for b in page["blocks"]]
        # A start point: every block can move, and each has its own id.
        assert not any(b["locked"] for b in blocks)
        assert len({b["id"] for b in blocks}) == len(blocks)
        # Everything lies on the page.
        assert all(0 <= b["x"] <= b["x"] + b["w"] <= 210 for b in blocks)
        assert all(0 <= b["y"] <= b["y"] + b["h"] <= 297 for b in blocks)

    sheet, test, labels = (t["doc"]["pages"] for t in built_in)
    # The name, the title and two empty areas.
    assert [kinds(page) for page in sheet] == [["name", "text", "rounded", "rounded"]]
    # Three pages, each with the name, the points total and numbered tasks with their points.
    assert len(test) == 3
    for page in test:
        assert kinds(page)[:2] == ["name", "points"]
        tasks = [b for b in page["blocks"] if b.get("mark") == "1."]
        assert tasks
        assert kinds(page).count("points") == 1 + len(tasks)
    # The title, the picture's area and lines with arrows to label it.
    assert [kinds(page)[:2] for page in labels] == [["text", "rect"]]
    assert kinds(labels[0]).count("line") == kinds(labels[0]).count("arrow") == 6


def test_templates_belong_to_one_user():
    client = user("a@example.com")
    other = user("b@example.com")
    doc = {"blocks": [], "guides": {"x": [70], "y": []}, "grid": 5}
    saved = client.post("/api/templates", json={"name": "Drei Spalten", "doc": doc}).json()
    assert own(client) == [{**saved, "name": "Drei Spalten", "doc": doc}]
    assert own(other) == []
    assert other.delete(f"/api/templates/{saved['id']}").status_code == 404
    assert client.delete(f"/api/templates/{saved['id']}").status_code == 200
    assert own(client) == []
    assert client.post("/api/templates", json={"name": "", "doc": doc}).status_code == 422


def test_sheets_belong_to_one_user():
    client = user("a@example.com")
    other = user("b@example.com")
    doc = {"pages": [{"blocks": []}], "guides": {"x": [], "y": []}, "grid": 0}
    sheet = client.post("/api/sheets", json={"title": "Plusaufgaben", "doc": doc}).json()
    url = f"/api/sheets/{sheet['id']}"
    assert sheet["title"] == "Plusaufgaben"
    assert sheet["doc"] == doc
    assert client.get(url).json() == sheet
    assert client.get("/api/sheets").json() == [sheet]

    # A save may bring the title, the document or both.
    grid = {**doc, "grid": 5}
    assert client.patch(url, json={"title": "Minusaufgaben"}).json()["doc"] == doc
    assert client.patch(url, json={"doc": grid, "version": 1}).json()["title"] == "Minusaufgaben"
    assert client.patch(url, json={"title": ""}).status_code == 422
    copy = client.post(f"{url}/duplicate").json()
    assert copy["id"] != sheet["id"]
    assert copy["title"] == "Minusaufgaben (Kopie)"
    assert copy["doc"] == grid
    assert {s["id"] for s in client.get("/api/sheets").json()} == {sheet["id"], copy["id"]}

    assert other.get("/api/sheets").json() == []
    assert other.get(url).status_code == 404
    assert other.patch(url, json={"title": "Geklaut"}).status_code == 404
    # Not a 409 either: that would tell a stranger the sheet is there.
    assert other.patch(url, json={"doc": doc, "version": 1}).status_code == 404
    assert other.patch(url, json={"doc": doc, "version": 2}).status_code == 404
    assert other.post(f"{url}/duplicate").status_code == 404
    assert other.delete(url).status_code == 404
    assert client.get(url).json()["title"] == "Minusaufgaben"

    assert client.delete(url).status_code == 200
    assert client.get(url).status_code == 404
    assert [s["id"] for s in client.get("/api/sheets").json()] == [copy["id"]]


def test_every_call_for_an_item_hides_other_users_items():
    """Walks the routes, so a new call for an item is checked without a new test."""
    client = user("a@example.com")
    other = user("b@example.com")
    sheet = client.post("/api/sheets", json={"title": "Meins", "doc": {}}).json()
    template = client.post("/api/templates", json={"name": "Meins", "doc": {}}).json()
    # Every id is 1, the first user's included, so one path fits every route.
    assert sheet["id"] == template["id"] == client.get("/api/me").json()["id"] == 1

    calls = [
        (method, re.sub(r"{\w+}", "1", path))
        for path, methods in app.openapi()["paths"].items()
        if path.startswith("/api/") and "{" in path
        for method in methods
    ]
    assert len(calls) >= 8
    for method, path in calls:
        assert other.request(method, path, json={}).status_code == 404, (method, path)

    assert client.get("/api/sheets").json() == [sheet]
    assert own(client) == [template]
    assert other.get("/api/sheets").json() == []
    assert own(other) == []


def test_stale_save_gets_409():
    client = user("a@example.com")
    doc = {"pages": [{"blocks": []}], "guides": {"x": [], "y": []}, "grid": 0}
    sheet = client.post("/api/sheets", json={"title": "Blatt", "doc": doc}).json()
    url = f"/api/sheets/{sheet['id']}"
    assert sheet["version"] == 1

    # A rename brings no document: it needs no version and leaves the version alone.
    assert client.patch(url, json={"title": "Umbenannt"}).json()["version"] == 1
    five = client.patch(url, json={"doc": {**doc, "grid": 5}, "version": 1}).json()
    assert five["version"] == 2
    assert five["title"] == "Umbenannt"

    # Another device still holds version 1.
    stale = {"title": "Veraltet", "doc": {**doc, "grid": 10}, "version": 1}
    assert client.patch(url, json=stale).status_code == 409
    assert client.get(url).json() == five
    assert client.patch(url, json={**stale, "version": 2}).json()["version"] == 3
    # A document with no version is turned down.
    assert client.patch(url, json={"doc": {**doc, "grid": 20}}).status_code == 422
    assert client.get(url).json()["doc"]["grid"] == 10
    # To overwrite, the stale device asks for the version first.
    forced = client.patch(url, json={**stale, "version": client.get(url).json()["version"]}).json()
    assert forced["version"] == 4
    assert forced["title"] == "Veraltet"
    assert client.post(f"{url}/duplicate").json()["version"] == 1


def test_maths_exercises():
    client = user("a@example.com")
    out = client.post("/api/maths", json=MATHS).json()
    assert len(out["exercises"]) == 3
    assert out["loosen"] is None
    assert client.post("/api/maths", json={**MATHS, "max": 0}).status_code == 422


def test_legal_pages_are_public():
    client = TestClient(app)
    assert "Impressum" in client.get("/impressum").text
    assert "Datenschutzerklärung" in client.get("/datenschutz").text


def test_legal_pages_say_blattomat():
    client = TestClient(app)
    for path in ("/impressum", "/datenschutz"):
        res = client.get(path)
        assert res.status_code == 200
        title, body = res.text.split("</title>")
        assert "Blattomat" in title and "Blattomat" in body
        # The old name is gone, however it was written.
        assert "blattwerk" not in res.text.lower()


def test_cli_help_says_blattomat(tmp_path):
    # No word after the command: it prints its help and fails. The command keeps its name.
    env = {**os.environ, "BLATTWERK_DATA_DIR": str(tmp_path)}
    res = subprocess.run(
        [sys.executable, "-m", "blattwerk"], capture_output=True, text=True, env=env
    )
    assert res.returncode != 0
    assert "Blattomat" in res.stderr
    assert "python -m blattwerk invite" in res.stderr
