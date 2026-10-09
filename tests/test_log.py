import importlib
import logging
import re

from fastapi.testclient import TestClient

import blattwerk
from blattwerk import auth, db
from blattwerk.app import app

# Time, level and logger name, as `docker logs` shows the line.
LINE = re.compile(
    r"^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d,\d{3} ERROR blattwerk\.auth: Could not delete (.+)$", re.M
)


def failed_delete(monkeypatch):
    """A user deletes the account and the folder stays, as on a full or read-only disk."""
    client = TestClient(app, base_url="https://testserver")
    login = {"email": "a@example.com", "password": "richtig-geheim"}
    token = auth.new_link(db.open_db())
    assert client.post("/api/signup", json={**login, "token": token}).status_code == 200
    client.post("/api/feedback", data={"text": "x"})
    monkeypatch.setattr(auth.shutil, "rmtree", lambda *args, **kwargs: None)
    monkeypatch.setattr(auth, "DELETE_WAIT", 0)
    assert client.delete("/api/me").status_code == 200


def test_error_line_carries_time_level_and_name(data_dir, monkeypatch, capfd):
    failed_delete(monkeypatch)
    err = capfd.readouterr().err
    assert LINE.findall(err) == [str(data_dir / "users" / "1")]


def test_line_shows_once_and_caplog_sees_it(data_dir, monkeypatch, capfd, caplog):
    failed_delete(monkeypatch)
    assert capfd.readouterr().err.count("Could not delete") == 1
    assert [r.name for r in caplog.records] == ["blattwerk.auth"]


def test_reload_adds_no_second_handler():
    importlib.reload(blattwerk)
    assert len(logging.getLogger("blattwerk").handlers) == 1
