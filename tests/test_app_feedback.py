"""Feedback lands in the user's folder, and deleting the account takes it with it."""

import json

from fastapi.testclient import TestClient
from test_app import (
    EMPTY,
    PASSWORD,
    user,
)

from blattwerk import db
from blattwerk.app import app


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


def test_feedback_from_the_app_drops_source(data_dir):
    client = user("a@example.com")
    res = client.post("/api/feedback", data={"text": "x", "source": "mcp"})
    out = data_dir / "users" / "1" / "feedback" / res.json()["saved"]
    assert json.loads((out / "feedback.json").read_text()) == {"text": "x"}


def test_feedback_with_a_bad_token_is_401(data_dir):
    client = TestClient(app, base_url="https://testserver")
    res = client.post("/api/feedback", data={"text": "x"}, headers={"Authorization": "Bearer nope"})
    assert res.status_code == 401


def test_feedback_by_token_stops_after_ten_in_a_while(data_dir):
    client = user("a@example.com")
    token = client.post("/api/tokens", json={"name": "mcp"}).json()["token"]
    bearer = TestClient(app, base_url="https://testserver")
    head = {"Authorization": f"Bearer {token}"}
    codes = [
        bearer.post("/api/feedback", data={"text": "x"}, headers=head).status_code
        for _ in range(11)
    ]
    assert codes == [200] * 10 + [429]
    # The app's own form is not counted.
    assert client.post("/api/feedback", data={"text": "x"}).status_code == 200


def test_delete_account_removes_user_and_feedback(data_dir):
    client = user("a@example.com")
    other = user("b@example.com")
    client.post("/api/sheets", json={"title": "Meins", "doc": EMPTY})
    other.post("/api/sheets", json={"title": "Deins", "doc": EMPTY})
    client.post("/api/feedback", data={"text": "x"})
    other.post("/api/feedback", data={"text": "y"})
    assert client.delete("/api/me").status_code == 200
    assert client.get("/api/me").status_code == 401
    assert not (data_dir / "users" / "1").exists()
    assert (data_dir / "users" / "2").exists()
    assert [r["title"] for r in db.open_db().execute("SELECT title FROM sheets")] == ["Deins"]
    login = {"email": "a@example.com", "password": PASSWORD}
    assert client.post("/api/login", json=login).status_code == 401
