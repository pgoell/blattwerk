"""Sign-up, login, logout, the rate limit and the admin's invites."""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from test_app import (
    EMPTY,
    MATHS,
    PASSWORD,
    invite,
    user,
)

from blattwerk import (
    auth,
    db,
)
from blattwerk.app import app


def test_logged_out_gets_401():
    client = TestClient(app, base_url="https://testserver")
    assert client.get("/api/me").status_code == 401
    assert client.post("/api/feedback", data={"text": "x"}).status_code == 401
    assert client.get("/api/admin/users").status_code == 401
    assert client.get("/api/templates").status_code == 401
    assert client.post("/api/templates", json={"name": "x", "doc": EMPTY}).status_code == 401
    assert client.delete("/api/templates/1").status_code == 401
    assert client.get("/api/sheets").status_code == 401
    assert client.post("/api/sheets", json={"title": "x", "doc": EMPTY}).status_code == 401
    assert client.get("/api/sheets/1").status_code == 401
    assert client.patch("/api/sheets/1", json={"title": "x"}).status_code == 401
    assert client.post("/api/sheets/1/duplicate").status_code == 401
    assert client.get("/api/sheets/1/share").status_code == 401
    assert client.post("/api/sheets/1/share").status_code == 401
    assert client.post("/api/sheets/1/share/renew").status_code == 401
    assert client.delete("/api/sheets/1/share").status_code == 401
    assert client.post("/api/shares/abc/copy").status_code == 401
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
