import logging
import os
import shutil
import time

import pytest
from fastapi.testclient import TestClient

from blattwerk import auth, db
from blattwerk.app import app

PASSWORD = "richtig-geheim"
LOGIN = {"email": "a@example.com", "password": PASSWORD}
# The real one: a test that swaps `auth.shutil.rmtree` swaps it for the whole process.
RMTREE = shutil.rmtree


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


def admin():
    client = TestClient(app, base_url="https://testserver")
    body = {**LOGIN, "email": "admin@example.com", "token": auth.new_link(db.open_db(), admin=True)}
    assert client.post("/api/signup", json=body).status_code == 200
    return client


def stuck(path, onexc):
    """Stands in for `shutil.rmtree` on a folder that will not go."""
    onexc(os.rmdir, str(path), PermissionError(13, "Permission denied", str(path)))


def leftover(monkeypatch, rmtree=stuck):
    """Deletes an account whose folder will not go. Gives the client and the folder."""
    client = user()
    client.post("/api/feedback", data={"text": "x"})
    monkeypatch.setattr(auth, "DELETE_WAIT", 0)
    monkeypatch.setattr(auth.shutil, "rmtree", rmtree)
    assert client.delete("/api/me").status_code == 200
    return client, db.DATA_DIR / "users" / "1"


def rows():
    con = db.open_db()
    try:
        return [tuple(row) for row in con.execute("SELECT * FROM leftovers")]
    finally:
        con.close()


def test_delete_retries_after_a_short_wait_until_the_folder_goes(data_dir, monkeypatch, caplog):
    client = user()
    client.post("/api/feedback", data={"text": "x"})
    folder = data_dir / "users" / "1"
    tries, waits = [], []

    def second_try_works(path, onexc):
        tries.append(path)
        (stuck if len(tries) < 2 else RMTREE)(path, onexc=onexc)

    monkeypatch.setattr(auth.shutil, "rmtree", second_try_works)
    monkeypatch.setattr(auth.time, "sleep", waits.append)
    assert client.delete("/api/me").status_code == 200
    assert tries == [folder, folder]
    assert waits == [auth.DELETE_WAIT]
    assert 0 < auth.DELETE_WAIT < 0.5
    assert not folder.exists()
    assert rows() == []
    assert not errors(caplog)


def test_folder_that_stays_is_remembered_past_a_restart(data_dir, monkeypatch):
    tries, waits = [], []

    def never(path, onexc):
        tries.append(path)
        stuck(path, onexc)

    monkeypatch.setattr(auth.time, "sleep", waits.append)
    _, folder = leftover(monkeypatch, never)
    assert len(tries) == auth.DELETE_TRIES == 3
    # A wait between two tries, none after the last.
    assert len(waits) == 2
    assert folder.exists()
    # A new connection and a new client, as after a restart.
    ((user_id, since, error),) = rows()
    assert user_id == 1
    assert error == f"PermissionError: [Errno 13] Permission denied: '{folder}'"
    assert admin().get("/api/admin/leftovers").json() == [
        {"folder": "users/1", "since": since, "error": error}
    ]


def test_folder_that_stays_with_no_error_is_remembered_too(data_dir, monkeypatch):
    leftover(monkeypatch, lambda path, onexc: None)
    ((_, _, error),) = rows()
    assert error == "The folder is still there"


def test_next_start_deletes_the_folder_and_forgets_it(data_dir, monkeypatch):
    _, folder = leftover(monkeypatch)
    monkeypatch.setattr(auth.shutil, "rmtree", RMTREE)
    auth.retry_leftovers()
    assert not folder.exists()
    assert rows() == []
    assert admin().get("/api/admin/leftovers").json() == []


def test_start_of_the_app_tries_the_left_over_folders(data_dir, monkeypatch):
    _, folder = leftover(monkeypatch)
    monkeypatch.setattr(auth.shutil, "rmtree", RMTREE)
    # `with` runs the start, as uvicorn does.
    with TestClient(app, base_url="https://testserver"):
        assert not folder.exists()
        assert rows() == []


def test_start_that_fails_again_keeps_since_and_writes_the_new_error(data_dir, monkeypatch):
    _, folder = leftover(monkeypatch)
    con = db.open_db()
    con.execute("UPDATE leftovers SET since = '2026-01-05 08:30:00'")
    con.close()

    def full(path, onexc):
        onexc(os.rmdir, str(path), OSError(30, "Read-only file system", str(path)))

    monkeypatch.setattr(auth.shutil, "rmtree", full)
    auth.retry_leftovers()
    assert folder.exists()
    error = f"OSError: [Errno 30] Read-only file system: '{folder}'"
    assert rows() == [(1, "2026-01-05 08:30:00", error)]


def test_folder_removed_by_hand_drops_the_alert_with_no_restart(data_dir, monkeypatch):
    _, folder = leftover(monkeypatch)
    client = admin()
    assert len(client.get("/api/admin/leftovers").json()) == 1
    RMTREE(folder)
    assert client.get("/api/admin/leftovers").json() == []
    assert rows() == []


def test_leftovers_do_not_exist_for_others(data_dir, monkeypatch):
    leftover(monkeypatch)
    assert user().get("/api/admin/leftovers").status_code == 404
    logged_out = TestClient(app, base_url="https://testserver")
    assert logged_out.get("/api/admin/leftovers").status_code == 401


def test_account_is_gone_in_under_a_second_though_the_folder_stays(data_dir, monkeypatch):
    client = user()
    client.post("/api/feedback", data={"text": "x"})
    monkeypatch.setattr(auth.shutil, "rmtree", stuck)
    # With the real waits.
    start = time.monotonic()
    assert client.delete("/api/me").status_code == 200
    assert time.monotonic() - start < 1
    assert gone(client)
    assert len(rows()) == 1


def test_alert_and_log_name_the_folder_never_the_email(data_dir, monkeypatch, caplog):
    _, folder = leftover(monkeypatch)
    (record,) = errors(caplog)
    assert str(folder) in record.getMessage()
    assert "a@example.com" not in caplog.text
    res = admin().get("/api/admin/leftovers")
    assert res.json()[0]["folder"] == "users/1"
    assert "a@example.com" not in res.text


def test_failed_folder_delete_is_logged(data_dir, monkeypatch, caplog):
    client = user()
    client.post("/api/feedback", data={"text": "x"})

    # The delete of the folder fails, as on a full or read-only disk.
    monkeypatch.setattr(auth, "DELETE_WAIT", 0)
    monkeypatch.setattr(auth.shutil, "rmtree", lambda *args, **kwargs: None)
    assert client.delete("/api/me").status_code == 200
    assert gone(client)
    (record,) = errors(caplog)
    assert record.levelno == logging.ERROR
    assert str(data_dir / "users" / "1") in record.getMessage()
    assert "a@example.com" not in caplog.text


@pytest.mark.skipif(os.geteuid() == 0, reason="root may delete from a read-only folder")
def test_read_only_folder_logs_one_line_and_the_rest_goes(data_dir, monkeypatch, caplog):
    monkeypatch.setattr(auth, "DELETE_WAIT", 0)
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
