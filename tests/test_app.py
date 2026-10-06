import json

import pytest
from fastapi.testclient import TestClient

from blattwerk import auth, db
from blattwerk.app import app

PASSWORD = "richtig-geheim"


@pytest.fixture(autouse=True)
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DATA_DIR", tmp_path)
    auth.attempts.clear()
    return tmp_path


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
            ("other", ("x", b"ignored", "image/jpeg")),
        ],
    )
    out = data_dir / "users" / "1" / "feedback" / res.json()["saved"]
    assert json.loads((out / "feedback.json").read_text()) == {"text": "Alles langsam"}
    assert (out / "audio-1.webm").read_bytes() == b"one"
    assert (out / "audio-2.m4a").read_bytes() == b"two"
    assert (out / "photo-1.jpg").read_bytes() == b"page1"
    assert len(list(out.iterdir())) == 4


def test_delete_account_removes_user_and_feedback(data_dir):
    client = user("a@example.com")
    other = user("b@example.com")
    client.post("/api/feedback", data={"text": "x"})
    other.post("/api/feedback", data={"text": "y"})
    assert client.delete("/api/me").status_code == 200
    assert client.get("/api/me").status_code == 401
    assert not (data_dir / "users" / "1").exists()
    assert (data_dir / "users" / "2").exists()
    login = {"email": "a@example.com", "password": PASSWORD}
    assert client.post("/api/login", json=login).status_code == 401


def test_templates_belong_to_one_user():
    client = user("a@example.com")
    other = user("b@example.com")
    doc = {"blocks": [], "guides": {"x": [70], "y": []}, "grid": 5}
    saved = client.post("/api/templates", json={"name": "Drei Spalten", "doc": doc}).json()
    assert client.get("/api/templates").json() == [{**saved, "name": "Drei Spalten", "doc": doc}]
    assert other.get("/api/templates").json() == []
    assert other.delete(f"/api/templates/{saved['id']}").status_code == 404
    assert client.delete(f"/api/templates/{saved['id']}").status_code == 200
    assert client.get("/api/templates").json() == []
    assert client.post("/api/templates", json={"name": "", "doc": doc}).status_code == 422


def test_legal_pages_are_public():
    client = TestClient(app)
    assert "Impressum" in client.get("/impressum").text
    assert "Datenschutzerklärung" in client.get("/datenschutz").text
