"""A deleted account, sheet, template or upload never reuses its id."""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from test_app import (
    EMPTY,
    PASSWORD,
    invite,
    my_id,
    restarted,
    user,
)
from ui import png

from blattwerk import (
    auth,
    db,
)


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


def test_deleted_sheet_id_is_not_reused():
    client = user("a@example.com")
    ids = [client.post("/api/sheets", json={"title": "x", "doc": EMPTY}).json()["id"] for _ in "ab"]
    assert ids == [1, 2]
    assert client.delete("/api/sheets/2").status_code == 200
    assert client.post("/api/sheets", json={"title": "x", "doc": EMPTY}).json()["id"] == 3
    assert client.delete("/api/sheets/3").status_code == 200
    again = restarted(client).post("/api/sheets", json={"title": "x", "doc": EMPTY})
    assert again.json()["id"] == 4


def test_deleted_template_id_is_not_reused():
    client = user("a@example.com")
    ids = [
        client.post("/api/templates", json={"name": "x", "doc": EMPTY}).json()["id"] for _ in "ab"
    ]
    assert ids == [1, 2]
    assert client.delete("/api/templates/2").status_code == 200
    assert client.post("/api/templates", json={"name": "x", "doc": EMPTY}).json()["id"] == 3
    assert client.delete("/api/templates/3").status_code == 200
    again = restarted(client).post("/api/templates", json={"name": "x", "doc": EMPTY})
    assert again.json()["id"] == 4


def test_deleted_upload_id_is_not_reused():
    """No call deletes one upload: its row goes with the account, here by hand."""
    client = user("a@example.com")
    picture = {"file": ("bild", png(), "image/png")}
    assert [client.post("/api/uploads", files=picture).json()["id"] for _ in "ab"] == [1, 2]
    con = db.open_db()
    con.execute("DELETE FROM uploads WHERE id = 2")
    assert client.post("/api/uploads", files=picture).json()["id"] == 3
    con.execute("DELETE FROM uploads WHERE id = 3")
    assert restarted(client).post("/api/uploads", files=picture).json()["id"] == 4
