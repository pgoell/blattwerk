import pytest
from fastapi.testclient import TestClient

from blattwerk import auth, db
from blattwerk.app import app
from blattwerk.uploads import MAX_BYTES

PASSWORD = "richtig-geheim"
PNG = b"\x89PNG\r\n\x1a\n not really a picture"


@pytest.fixture(autouse=True)
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DATA_DIR", tmp_path)
    auth.attempts.clear()
    return tmp_path


def user(email):
    """A client logged in as a new user. https, or the Secure cookie is not sent back."""
    client = TestClient(app, base_url="https://testserver")
    body = {"token": auth.new_link(db.open_db()), "email": email, "password": PASSWORD}
    assert client.post("/api/signup", json=body).status_code == 200
    return client


def send(client, data=PNG, kind="image/png"):
    return client.post("/api/uploads", files={"file": ("bild", data, kind)})


def test_logged_out_gets_401():
    client = TestClient(app, base_url="https://testserver")
    assert send(client).status_code == 401
    assert client.get("/api/uploads/1").status_code == 401


def test_upload_comes_back_as_sent(data_dir):
    client = user("a@example.com")
    upload_id = send(client).json()["id"]
    res = client.get(f"/api/uploads/{upload_id}")
    assert res.content == PNG
    assert res.headers["content-type"] == "image/png"
    assert (data_dir / "users" / "1" / "uploads" / str(upload_id)).read_bytes() == PNG
    assert client.get("/api/uploads/99").status_code == 404


def test_uploads_belong_to_one_user():
    client = user("a@example.com")
    other = user("b@example.com")
    upload_id = send(client).json()["id"]
    assert other.get(f"/api/uploads/{upload_id}").status_code == 404
    # An upload of their own does not open the first user's either.
    assert send(other).json()["id"] != upload_id
    assert other.get(f"/api/uploads/{upload_id}").status_code == 404
    assert client.get(f"/api/uploads/{upload_id}").status_code == 200


def test_only_pictures_of_a_sane_size():
    client = user("a@example.com")
    assert send(client, b"<svg onload='alert(1)'/>", "image/svg+xml").status_code == 415
    assert send(client, b"%PDF", "application/pdf").status_code == 415
    assert send(client, b"x" * (MAX_BYTES + 1)).status_code == 413
    assert db.open_db().execute("SELECT count(*) FROM uploads").fetchone()[0] == 0


def test_delete_account_removes_uploads(data_dir):
    client = user("a@example.com")
    other = user("b@example.com")
    send(client)
    kept = send(other).json()["id"]
    assert client.delete("/api/me").status_code == 200
    assert not (data_dir / "users" / "1").exists()
    assert [r["user_id"] for r in db.open_db().execute("SELECT user_id FROM uploads")] == [2]
    assert other.get(f"/api/uploads/{kept}").content == PNG
