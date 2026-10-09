import logging
import os

import pytest
from fastapi.testclient import TestClient

from blattwerk import auth, db
from blattwerk.app import app

PASSWORD = "richtig-geheim"
LOGIN = {"email": "a@example.com", "password": PASSWORD}


def user():
    """A client logged in as a new user. https, or the Secure cookie is not sent back."""
    client = TestClient(app, base_url="https://testserver")
    token = auth.new_link(db.open_db())
    assert client.post("/api/signup", json={**LOGIN, "token": token}).status_code == 200
    return client


def errors(caplog):
    return [r for r in caplog.records if r.name == "blattwerk.auth"]


def gone(client):
    return client.get("/api/me").status_code == 401 and (
        client.post("/api/login", json=LOGIN).status_code == 401
    )


def test_failed_folder_delete_is_logged(data_dir, monkeypatch, caplog):
    client = user()
    client.post("/api/feedback", data={"text": "x"})

    # The delete of the folder fails, as on a full or read-only disk.
    monkeypatch.setattr(auth.shutil, "rmtree", lambda *args, **kwargs: None)
    assert client.delete("/api/me").status_code == 200
    assert gone(client)
    (record,) = errors(caplog)
    assert record.levelno == logging.ERROR
    assert str(data_dir / "users" / "1") in record.getMessage()
    assert "a@example.com" not in caplog.text


@pytest.mark.skipif(os.geteuid() == 0, reason="root may delete from a read-only folder")
def test_read_only_folder_logs_one_line_and_the_rest_goes(data_dir, caplog):
    client = user()
    for text in "wxyz":
        client.post("/api/feedback", data={"text": text})
    folder = data_dir / "users" / "1"
    sends = sorted((folder / "feedback").iterdir())
    locked = sends[1:3]
    for path in locked:
        path.chmod(0o500)
    try:
        assert client.delete("/api/me").status_code == 200
    finally:
        # Or pytest cannot clear its temp folder.
        for path in locked:
            path.chmod(0o700)
    assert gone(client)
    # What can go is gone, whichever send the delete met first.
    assert sorted((folder / "feedback").iterdir()) == locked
    (record,) = errors(caplog)
    assert record.levelno == logging.ERROR
    assert str(folder) in record.getMessage()


def test_account_without_a_folder_logs_nothing(data_dir, caplog):
    client = user()
    assert not (data_dir / "users" / "1").exists()
    assert client.delete("/api/me").status_code == 200
    assert gone(client)
    assert not caplog.records
