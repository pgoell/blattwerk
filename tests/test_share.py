"""A share link: on and off, a frozen preview, a copy with pictures, a dead link after delete.

The preview is the sheet as it was when the link was made or last renewed. The copy lands in the
receiver's account, named after the sheet and nothing else, and neither sheet's later edits
reach the other.
"""

import json
import os
import time

from fastapi.testclient import TestClient
from ui import TEXT, block, picture, png, sheet, upload, user

from blattwerk import db, pictures
from blattwerk.app import app

WALL = {
    "base": 3,
    "count": 4,
    "columns": 2,
    "max": 20,
    "op": "+",
    "given": "base",
    "empty": False,
    "seed": 7,
}
PREFIX = "Kopie von "


def guest():
    return TestClient(app, base_url="https://testserver")


def wall(seed=7):
    return block("zahlenmauer", 20, 60, {**WALL, "seed": seed})


def made(owner, upload_id, title="Sachaufgaben"):
    """Two pages: a picture and a wall on the first, a line of text on the second."""
    return sheet(owner, [picture(upload_id), wall()], [block("text", 20, 20, TEXT)], title=title)


def turn_on(owner, sheet_id):
    res = owner.post(f"/api/sheets/{sheet_id}/share")
    assert res.status_code == 200
    return res.json()


def seed_of(doc):
    return next(b["props"]["seed"] for b in doc["pages"][0]["blocks"] if b["type"] == "zahlenmauer")


def image_of(doc):
    return next(b["props"]["upload"] for b in doc["pages"][0]["blocks"] if b["type"] == "image")


def age(upload_id, owner):
    then = time.time() - (pictures.KEEP_DAYS + 1) * 86400
    os.utime(pictures.path(owner, upload_id), (then, then))


def no_cookie(res):
    assert res.headers.get("set-cookie") is None


def test_logged_out_cannot_switch_a_link_or_take_a_copy():
    client = guest()
    assert client.get("/api/sheets/1/share").status_code == 401
    assert client.post("/api/sheets/1/share").status_code == 401
    assert client.post("/api/sheets/1/share/renew").status_code == 401
    assert client.delete("/api/sheets/1/share").status_code == 401
    assert client.post("/api/shares/abc/copy").status_code == 401
    no_cookie(client.post("/api/shares/abc/copy"))


def test_link_turns_on_and_off():
    """The owner sees that the link is on, and switching it off kills that token."""
    owner = user()
    made_sheet = made(owner, upload(owner))
    assert owner.get(f"/api/sheets/{made_sheet['id']}/share").json() == {"on": False}
    first = turn_on(owner, made_sheet["id"])
    assert first["on"] is True
    assert len(first["token"]) >= 40
    again = turn_on(owner, made_sheet["id"])
    assert again["token"] == first["token"]
    guest_view = guest().get(f"/api/shares/{first['token']}")
    assert guest_view.status_code == 200
    assert owner.delete(f"/api/sheets/{made_sheet['id']}/share").json() == {"on": False}
    assert owner.get(f"/api/sheets/{made_sheet['id']}/share").json() == {"on": False}
    assert guest().get(f"/api/shares/{first['token']}").status_code == 404
    assert owner.post(f"/api/shares/{first['token']}/copy").status_code == 404
    # A new link is a new token. The old one stays dead.
    second = turn_on(owner, made_sheet["id"])
    assert second["token"] != first["token"]
    assert guest().get(f"/api/shares/{second['token']}").status_code == 200
    # Someone else's sheet is as missing as one that never was.
    stranger = user()
    assert stranger.post(f"/api/sheets/{made_sheet['id']}/share").status_code == 404
    assert guest().get("/api/shares").status_code == 404


def test_preview_sets_no_cookie_and_names_no_owner():
    owner = user()
    email = owner.get("/api/me").json()["email"]
    made_sheet = made(owner, upload(owner), title="Ä" * 80)
    token = turn_on(owner, made_sheet["id"])["token"]
    res = guest().get(f"/api/shares/{token}")
    assert res.status_code == 200
    no_cookie(res)
    assert res.headers["x-robots-tag"] == "noindex, nofollow"
    assert res.headers["cache-control"] == "no-store"
    assert set(res.json()) == {"title", "doc"}
    assert email not in res.text
    assert "user_id" not in res.json()
    page = guest().get(f"/teilen/{token}")
    assert page.status_code == 200
    no_cookie(page)
    assert "noindex" in page.headers["x-robots-tag"]


def test_preview_is_the_snapshot_until_it_is_renewed():
    owner = user()
    upload_id = upload(owner)
    made_sheet = made(owner, upload_id)
    token = turn_on(owner, made_sheet["id"])["token"]
    changed = {
        "doc": {
            "pages": [{"blocks": [wall(seed=9)]}, {"blocks": []}],
            "guides": {"x": [], "y": []},
            "grid": 0,
        },
        "version": made_sheet["version"],
    }
    saved = owner.patch(f"/api/sheets/{made_sheet['id']}", json=changed)
    assert saved.status_code == 200
    preview = guest().get(f"/api/shares/{token}").json()
    assert seed_of(preview["doc"]) == 7
    assert image_of(preview["doc"]) == upload_id
    picture_bytes = guest().get(f"/api/shares/{token}/uploads/{upload_id}")
    assert picture_bytes.status_code == 200
    assert picture_bytes.content == png()
    no_cookie(picture_bytes)
    # A picture the snapshot does not show is as missing as one that never was.
    other_upload = upload(owner)
    assert guest().get(f"/api/shares/{token}/uploads/{other_upload}").status_code == 404
    renewed = owner.post(f"/api/sheets/{made_sheet['id']}/share/renew")
    assert renewed.status_code == 200
    assert renewed.json()["token"] == token
    assert seed_of(guest().get(f"/api/shares/{token}").json()["doc"]) == 9
    assert guest().get(f"/api/shares/{token}/uploads/{upload_id}").status_code == 404


def test_copy_brings_pictures_seeds_and_pages_and_stays_apart(data_dir):
    owner = user()
    other = user()
    email = owner.get("/api/me").json()["email"]
    upload_id = upload(owner)
    title = "Ä" * 80
    made_sheet = made(owner, upload_id, title=title)
    token = turn_on(owner, made_sheet["id"])["token"]
    copied = other.post(f"/api/shares/{token}/copy")
    assert copied.status_code == 200
    copy = copied.json()
    assert copy["title"] == PREFIX + "Ä" * 70
    assert len(copy["title"]) == 80
    assert email not in copied.text
    assert copy["user_id"] == other.get("/api/me").json()["id"]
    assert copy["user_id"] != made_sheet["user_id"]
    assert len(copy["doc"]["pages"]) == 2
    assert copy["doc"]["pages"][1]["blocks"][0]["props"]["text"] == "Hallo"
    assert seed_of(copy["doc"]) == 7
    copied_upload = image_of(copy["doc"])
    assert copied_upload != upload_id
    assert other.get(f"/api/uploads/{copied_upload}").content == png()
    assert other.get(f"/api/uploads/{upload_id}").status_code == 404
    owner_file = data_dir / "users" / str(made_sheet["user_id"]) / "uploads" / str(upload_id)
    copy_file = data_dir / "users" / str(copy["user_id"]) / "uploads" / str(copied_upload)
    assert owner_file.read_bytes() == copy_file.read_bytes() == png()
    # The copy is a sheet of its own: neither side's next save reaches the other.
    owner_body = {
        "doc": {
            "pages": [{"blocks": [wall(seed=9)]}, {"blocks": []}],
            "guides": {"x": [], "y": []},
            "grid": 0,
        },
        "version": made_sheet["version"],
    }
    assert owner.patch(f"/api/sheets/{made_sheet['id']}", json=owner_body).status_code == 200
    assert seed_of(other.get(f"/api/sheets/{copy['id']}").json()["doc"]) == 7
    assert other.get(f"/api/uploads/{copied_upload}").content == png()
    copy_body = {"doc": copy["doc"], "version": copy["version"]}
    copy_body["doc"]["pages"][0]["blocks"][1]["props"]["seed"] = 3
    assert other.patch(f"/api/sheets/{copy['id']}", json=copy_body).status_code == 200
    assert seed_of(owner.get(f"/api/sheets/{made_sheet['id']}").json()["doc"]) == 9
    # Nothing on the copy points back, and the owner's list did not gain a sheet.
    assert "source" not in json.dumps(copy)
    assert [row["id"] for row in owner.get("/api/sheets").json()] == [made_sheet["id"]]
    assert [row["id"] for row in other.get("/api/sheets").json()] == [copy["id"]]


def test_a_picture_only_the_link_shows_stays():
    """Taking the picture off the sheet does not take it off a link that still shows it."""
    owner = user()
    upload_id = upload(owner)
    made_sheet = made(owner, upload_id)
    token = turn_on(owner, made_sheet["id"])["token"]
    emptied = {
        "doc": {
            "pages": [{"blocks": []}],
            "guides": {"x": [], "y": []},
            "grid": 0,
        },
        "version": made_sheet["version"],
    }
    saved = owner.patch(f"/api/sheets/{made_sheet['id']}", json=emptied).json()
    age(upload_id, made_sheet["user_id"])
    # A save sweeps. The link still shows the picture, so the file stays.
    saved = owner.patch(
        f"/api/sheets/{made_sheet['id']}",
        json={"doc": saved["doc"], "version": saved["version"]},
    ).json()
    assert pictures.path(made_sheet["user_id"], upload_id).is_file()
    assert guest().get(f"/api/shares/{token}/uploads/{upload_id}").content == png()
    assert owner.delete(f"/api/sheets/{made_sheet['id']}/share").status_code == 200
    age(upload_id, made_sheet["user_id"])
    assert (
        owner.patch(
            f"/api/sheets/{made_sheet['id']}",
            json={"doc": saved["doc"], "version": saved["version"]},
        ).status_code
        == 200
    )
    assert not pictures.path(made_sheet["user_id"], upload_id).is_file()


def test_copy_stops_at_the_free_sheet_cap(monkeypatch):
    """A copy is a new sheet, so the same cap as create and duplicate applies."""
    monkeypatch.setenv("BLATTWERK_FREE_SHEETS", "1")
    owner = user()
    other = user()
    made_sheet = made(owner, upload(owner))
    token = turn_on(owner, made_sheet["id"])["token"]
    own = other.post(
        "/api/sheets",
        json={
            "title": "Eigenes",
            "doc": {"pages": [{"blocks": []}], "guides": {"x": [], "y": []}, "grid": 0},
        },
    )
    assert own.status_code == 200
    blocked = other.post(f"/api/shares/{token}/copy")
    assert blocked.status_code == 402
    assert "39" not in blocked.text
    assert [row["id"] for row in other.get("/api/sheets").json()] == [own.json()["id"]]
    # A link that is not there stays missing, even at the cap.
    assert other.post("/api/shares/" + "a" * 43 + "/copy").status_code == 404


def test_a_ground_is_on_the_preview_and_the_copy_has_its_own():
    """A page ground is a picture the link shows, and the copy points at its own file."""
    owner = user()
    other = user()
    upload_id = upload(owner)
    page = {
        "blocks": [],
        "ground": {"upload": upload_id, "ratio": 1.5, "cut": [0, 0, 0, 0]},
    }
    made_sheet = sheet(owner, page, title="Grund")
    token = turn_on(owner, made_sheet["id"])["token"]
    preview = guest().get(f"/api/shares/{token}")
    assert preview.status_code == 200
    assert preview.json()["doc"]["pages"][0]["ground"]["upload"] == upload_id
    got = guest().get(f"/api/shares/{token}/uploads/{upload_id}")
    assert got.status_code == 200
    assert got.content == png()
    copied = other.post(f"/api/shares/{token}/copy")
    assert copied.status_code == 200
    new_id = copied.json()["doc"]["pages"][0]["ground"]["upload"]
    assert new_id != upload_id
    assert other.get(f"/api/uploads/{new_id}").content == png()
    assert other.get(f"/api/uploads/{upload_id}").status_code == 404


def test_deleted_sheet_kills_the_link():
    owner = user()
    made_sheet = made(owner, upload(owner))
    token = turn_on(owner, made_sheet["id"])["token"]
    assert owner.delete(f"/api/sheets/{made_sheet['id']}").status_code == 200
    assert guest().get(f"/api/shares/{token}").status_code == 404
    other = user()
    assert other.post(f"/api/shares/{token}/copy").status_code == 404
    assert db.open_db().execute("SELECT count(*) FROM shares").fetchone()[0] == 0


def test_deleted_account_kills_the_link():
    owner = user()
    made_sheet = made(owner, upload(owner))
    token = turn_on(owner, made_sheet["id"])["token"]
    assert owner.delete("/api/me").status_code == 200
    assert guest().get(f"/api/shares/{token}").status_code == 404
    other = user()
    assert other.post(f"/api/shares/{token}/copy").status_code == 404
    assert db.open_db().execute("SELECT count(*) FROM shares").fetchone()[0] == 0
