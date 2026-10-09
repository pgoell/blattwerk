import sqlite3

import pytest
from fastapi.testclient import TestClient

from blattwerk import db
from blattwerk.app import app


@pytest.fixture
def reader(data_dir, monkeypatch):
    """Another connection that reads the new, empty database file and keeps its read open."""
    monkeypatch.setattr(db, "WAIT", 0.1)
    con = sqlite3.connect(data_dir / "blattwerk.db", autocommit=True, check_same_thread=False)
    con.execute("BEGIN")
    con.execute("SELECT * FROM sqlite_master").fetchall()
    yield con
    con.close()


def test_first_open_beside_a_reader_answers_503_and_the_next_makes_the_tables(reader):
    client = TestClient(app, base_url="https://testserver")
    res = client.get("/api/me")
    assert res.status_code == 503
    assert res.headers["retry-after"] == "1"
    reader.execute("ROLLBACK")
    assert client.get("/api/me").status_code == 401
    assert db.open_db().execute("SELECT count(*) FROM leftovers").fetchone()[0] == 0


def test_start_beside_a_reader_does_not_stop_the_app(reader, caplog):
    # `with` runs the start, as uvicorn does.
    with TestClient(app, base_url="https://testserver") as client:
        assert "Could not retry the left over folders" in caplog.text
        assert client.get("/api/me").status_code == 503
        reader.execute("ROLLBACK")
        assert client.get("/api/me").status_code == 401


def test_start_makes_the_tables_of_a_new_file(data_dir):
    with TestClient(app, base_url="https://testserver"):
        con = sqlite3.connect(data_dir / "blattwerk.db")
        assert con.execute("SELECT count(*) FROM leftovers").fetchone()[0] == 0


def test_another_error_of_the_open_is_not_a_503(data_dir):
    # A folder where the file should be: SQLite cannot open it.
    (data_dir / "blattwerk.db").mkdir()
    with pytest.raises(sqlite3.OperationalError, match="unable to open"):
        TestClient(app, base_url="https://testserver").get("/api/me")
