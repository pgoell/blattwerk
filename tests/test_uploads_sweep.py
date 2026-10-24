"""An upload no sheet shows is swept after 30 days. One a sheet still shows stays."""

import os
import sqlite3
import threading
import time
from pathlib import Path

import pytest
from test_uploads import PNG, send, user
from ui import picture, sheet

from blattwerk import db, pictures, svg, uploads


def doc(*blocks):
    return {"pages": [{"blocks": list(blocks)}], "guides": {"x": [], "y": []}, "grid": 0}


def save(client, made, *blocks):
    """Saves the sheet with these blocks alone, as the editor does."""
    body = {"doc": doc(*blocks), "version": made["version"]}
    res = client.patch(f"/api/sheets/{made['id']}", json=body)
    assert res.status_code == 200
    return res.json()


def age(upload_id, owner=1):
    """Makes the file a day older than a picture that nothing shows is kept."""
    then = time.time() - (pictures.KEEP_DAYS + 1) * 86400
    os.utime(pictures.path(owner, upload_id), (then, then))


def fresh(upload_id, owner=1):
    return pictures.path(owner, upload_id).stat().st_mtime > time.time() - 60


def there(upload_id, owner=1):
    """Whether the upload has its row and its file. Fails if it has one without the other."""
    row = db.open_db().execute("SELECT 1 FROM uploads WHERE id = ?", (upload_id,)).fetchone()
    file = pictures.path(owner, upload_id).is_file()
    assert bool(row) == file
    return file


def later_save(client):
    """Any save of the owner sweeps their uploads."""
    save(client, sheet(client, []))


@pytest.mark.parametrize("gone", ["block", "sheet", "template"])
def test_upload_nothing_shows_goes_after_30_days(gone):
    client = user("a@example.com")
    upload_id = send(client).json()["id"]
    if gone == "template":
        body = {"name": "x", "doc": doc(picture(upload_id))}
        made = client.post("/api/templates", json=body).json()
    else:
        made = sheet(client, [picture(upload_id)])
    # Neither the picture nor what shows it was saved for a long time.
    age(upload_id)
    if gone == "block":
        save(client, made)
    else:
        assert client.delete(f"/api/{gone}s/{made['id']}").status_code == 200
    # The 30 days count from here: undo may still bring the picture back.
    assert there(upload_id)
    assert fresh(upload_id)
    age(upload_id)
    later_save(client)
    assert not there(upload_id)
    assert client.get(f"/api/uploads/{upload_id}").status_code == 404


@pytest.mark.parametrize("by", ["sheet", "template"])
def test_upload_still_shown_stays_however_old(by):
    client = user("a@example.com")
    upload_id = send(client).json()["id"]
    if by == "sheet":
        sheet(client, [picture(upload_id)])
    else:
        body = {"name": "x", "doc": doc(picture(upload_id))}
        assert client.post("/api/templates", json=body).status_code == 200
    age(upload_id)
    later_save(client)
    assert there(upload_id)
    # The sweep found it shown, so it does not ask again for 30 days.
    assert fresh(upload_id)
    assert client.get(f"/api/uploads/{upload_id}").content == PNG


def test_picture_taken_off_an_old_sheet_comes_back():
    client = user("a@example.com")
    upload_id = send(client).json()["id"]
    made = sheet(client, [picture(upload_id)])
    age(upload_id)
    made = save(client, made)
    assert there(upload_id)
    assert client.get(f"/api/uploads/{upload_id}").content == PNG
    # Undo saves the sheet with the picture again.
    save(client, made, picture(upload_id))
    assert there(upload_id)
    assert client.get(f"/api/uploads/{upload_id}").content == PNG


def test_fresh_upload_on_no_sheet_stays():
    client = user("a@example.com")
    upload_id = send(client).json()["id"]
    later_save(client)
    assert there(upload_id)
    assert client.get(f"/api/uploads/{upload_id}").content == PNG


def test_only_the_owners_sheets_keep_an_upload():
    client = user("a@example.com")
    other = user("b@example.com")
    upload_id = send(client).json()["id"]
    theirs = send(other).json()["id"]
    age(upload_id)
    age(theirs, owner=2)
    # Another account's sheet and template name the id: they neither keep nor touch the file.
    sheet(other, [picture(upload_id)])
    body = {"name": "x", "doc": doc(picture(upload_id))}
    assert other.post("/api/templates", json=body).status_code == 200
    assert not fresh(upload_id)
    later_save(client)
    assert not there(upload_id)
    # The sweep of one account leaves the other's uploads alone, old and unshown as they are.
    assert there(theirs, owner=2)
    assert not fresh(theirs, owner=2)


def test_file_the_sweep_cannot_delete_keeps_its_row(monkeypatch, caplog):
    client = user("a@example.com")
    upload_id = send(client).json()["id"]
    age(upload_id)
    unlink = Path.unlink

    def refuse(self, missing_ok=False):
        monkeypatch.setattr(Path, "unlink", unlink)
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr(Path, "unlink", refuse)
    later_save(client)
    assert there(upload_id)
    errors = [r.getMessage() for r in caplog.records if r.levelname == "ERROR"]
    assert errors == [f"Could not delete {pictures.path(1, upload_id)}"]
    later_save(client)
    assert not there(upload_id)


def test_file_that_takes_no_time_does_not_fail_the_save(monkeypatch):
    client = user("a@example.com")
    upload_id = send(client).json()["id"]
    made = sheet(client, [picture(upload_id)])
    age(upload_id)

    def refuse(*args, **kwargs):
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr(pictures.os, "utime", refuse)
    assert save(client, made, picture(upload_id))["version"] == made["version"] + 1
    assert there(upload_id)


def test_busy_database_in_the_sweep_does_not_fail_a_stored_save_or_delete(monkeypatch, caplog):
    client = user("a@example.com")
    upload_id = send(client).json()["id"]
    made = sheet(client, [picture(upload_id)])

    def busy(con, user_id):
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(pictures, "clear", busy)
    assert save(client, made)["version"] == made["version"] + 1
    assert client.delete(f"/api/sheets/{made['id']}").status_code == 200
    assert caplog.text.count("Could not sweep the uploads of user 1") == 2
    assert there(upload_id)


def test_row_whose_file_is_gone_answers_404():
    client = user("a@example.com")
    upload_id = send(client).json()["id"]
    pictures.path(1, upload_id).unlink()
    assert client.get(f"/api/uploads/{upload_id}").status_code == 404


def test_template_from_before_pages_keeps_its_picture():
    client = user("a@example.com")
    upload_id = send(client).json()["id"]
    body = {"name": "alt", "doc": {"blocks": [picture(upload_id)]}}
    assert client.post("/api/templates", json=body).status_code == 200
    age(upload_id)
    later_save(client)
    assert there(upload_id)
    assert fresh(upload_id)


def test_file_of_another_system_user_is_never_swept(monkeypatch):
    # Such a file takes no time from the app, so the save that took its picture away left it old.
    client = user("a@example.com")
    upload_id = send(client).json()["id"]
    made = sheet(client, [picture(upload_id)])
    age(upload_id)
    other = os.geteuid() + 1
    monkeypatch.setattr(pictures.os, "geteuid", lambda: other)
    save(client, made)
    later_save(client)
    assert there(upload_id)


def test_no_more_than_two_svgs_are_parsed_at_once(monkeypatch):
    """A teacher's many uploads at once do not each take their memory: two parse, the rest wait."""
    now, most, lock = 0, 0, threading.Lock()

    def slow(data):
        nonlocal now, most
        with lock:
            now += 1
            most = max(most, now)
        time.sleep(0.05)
        with lock:
            now -= 1
        return data

    monkeypatch.setattr(svg, "clean", slow)
    threads = [threading.Thread(target=uploads.parsed, args=(b"<svg/>",)) for _ in range(6)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert most == 2
