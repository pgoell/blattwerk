"""The school folder (issue #93).

A teacher with a seat puts a copy of her sheet in. Another teacher at that school takes her own
copy out. The author and the school admin can delete. A teacher who leaves loses the folder, and
the sheet she put in stays. Another school sees nothing.
"""

# The fixture `window` is imported, and the test names it as its argument.
# ruff: noqa: F811

import re

from fastapi.testclient import TestClient
from playwright.sync_api import expect
from test_loading import window  # noqa: F401
from ui import PASSWORD, TEXT, box, picture, png, sheet, upload

from blattwerk import auth, db
from blattwerk.app import app

STAMP = re.compile(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}")


def sign_in(email, admin=False):
    client = TestClient(app, base_url="https://testserver")
    token = auth.new_link(db.open_db(), admin=admin)
    body = {"token": token, "email": email, "password": PASSWORD}
    assert client.post("/api/signup", json=body).status_code == 200
    return client


def give_seat(boss, school_id, email, admin=False):
    res = boss.post(
        f"/api/admin/schools/{school_id}/seats",
        json={"email": email, "admin": admin},
    )
    assert res.status_code == 200, res.text
    return res.json()


def seat_school(name="Waldschule"):
    """A site admin, a school, and two teachers: Anna runs it, Bea has a seat."""
    boss = sign_in("admin@example.com", admin=True)
    anna = sign_in("anna@example.com")
    bea = sign_in("bea@example.com")
    made = boss.post("/api/admin/schools", json={"name": name})
    assert made.status_code == 200, made.text
    school = made.json()
    give_seat(boss, school["id"], "anna@example.com", admin=True)
    give_seat(boss, school["id"], "bea@example.com")
    return boss, anna, bea, school


def put(client, title, label):
    made = sheet(client, [box("a", "text", TEXT)], title=title)
    res = client.post("/api/folder", json={"sheet_id": made["id"], "label": f"  {label}  "})
    assert res.status_code == 200, res.text
    return res.json()["sheet"], made


def titles(client, **params):
    res = client.get("/api/folder", params=params)
    assert res.status_code == 200, res.text
    return [row["title"] for row in res.json()["sheets"]]


def test_put_in_copies_the_sheet_with_the_teachers_name_and_the_date():
    """#93: putting a sheet in stores a copy, her name and the date, and her sheet stays hers."""
    _boss, anna, bea, _school = seat_school()
    made = sheet(anna, [box("a", "text", TEXT)], title="Plusaufgaben")
    assert (
        bea.post("/api/folder", json={"sheet_id": made["id"], "label": "Klasse 2"}).status_code
        == 404
    )
    res = anna.post("/api/folder", json={"sheet_id": made["id"], "label": "  Klasse 2  "})
    assert res.status_code == 200, res.text
    entry = res.json()["sheet"]
    assert res.json()["school"]["name"] == "Waldschule"
    assert entry["title"] == "Plusaufgaben"
    assert entry["label"] == "Klasse 2"
    assert entry["author_name"] == "anna"
    assert entry["mine"] is True
    assert STAMP.fullmatch(entry["created"])
    assert entry["updated"] >= entry["created"]
    assert entry["doc"] == made["doc"]
    assert anna.get(f"/api/sheets/{made['id']}").json()["title"] == "Plusaufgaben"
    anna.patch(f"/api/sheets/{made['id']}", json={"title": "Anders"})
    assert anna.get(f"/api/folder/{entry['id']}").json()["sheet"]["title"] == "Plusaufgaben"
    assert anna.get(f"/api/folder/{entry['id']}").json()["sheet"]["doc"] == made["doc"]
    seen = bea.get("/api/folder").json()
    assert seen["school"]["admin"] is False
    assert seen["sheets"][0]["author_name"] == "anna"
    assert seen["sheets"][0]["mine"] is False
    assert (
        anna.post("/api/folder", json={"sheet_id": made["id"], "label": "x" * 41}).status_code
        == 422
    )


def test_copy_out_is_her_own_sheet():
    """#93: the copy out is a new sheet. Editing one leaves the other alone."""
    _boss, anna, bea, _school = seat_school()
    entry, made = put(anna, "Plusaufgaben", "Klasse 2")
    copied = bea.post(f"/api/folder/{entry['id']}/copy")
    assert copied.status_code == 200, copied.text
    own = copied.json()
    assert own["title"] == "Kopie von Plusaufgaben"
    assert own["doc"] == entry["doc"]
    assert own["user_id"] == bea.get("/api/me").json()["id"]
    assert {row["id"] for row in bea.get("/api/sheets").json()} == {own["id"]}
    assert bea.patch(f"/api/sheets/{own['id']}", json={"title": "Meins"}).status_code == 200
    assert anna.get(f"/api/folder/{entry['id']}").json()["sheet"]["title"] == "Plusaufgaben"
    anna.patch(f"/api/sheets/{made['id']}", json={"doc": made["doc"], "version": made["version"]})
    assert bea.get(f"/api/sheets/{own['id']}").json()["doc"] == entry["doc"]
    long = "a" * 80
    huge, _ = put(anna, long, "")
    assert len(bea.post(f"/api/folder/{huge['id']}/copy").json()["title"]) == 80


def test_author_and_school_admin_delete_and_another_teacher_cannot():
    """#93: the author and the school admin delete. Another teacher at the school cannot."""
    boss, anna, bea, school = seat_school()
    cara = sign_in("cara@example.com")
    give_seat(boss, school["id"], "cara@example.com")
    entry, _made = put(bea, "Von Bea", "Mathe")
    assert cara.delete(f"/api/folder/{entry['id']}").status_code == 404
    assert anna.get(f"/api/folder/{entry['id']}").status_code == 200
    assert bea.delete(f"/api/folder/{entry['id']}").status_code == 200
    assert anna.get(f"/api/folder/{entry['id']}").status_code == 404
    again, _made = put(bea, "Noch eins", "")
    assert anna.delete(f"/api/folder/{again['id']}").status_code == 200
    assert bea.get("/api/folder").json()["sheets"] == []


def test_leaving_the_school_loses_the_folder_and_the_sheet_stays():
    """#93: a teacher who leaves cannot open the folder. What she put in stays for the others."""
    boss, anna, bea, school = seat_school()
    entry, _made = put(bea, "Bleibt", "Klasse 2")
    sheet(bea, [box("a", "text", TEXT)], title="Privat")
    user_id = bea.get("/api/me").json()["id"]
    assert boss.delete(f"/api/admin/schools/{school['id']}/seats/{user_id}").status_code == 200
    assert bea.get("/api/folder").status_code == 404
    assert bea.get(f"/api/folder/{entry['id']}").status_code == 404
    assert bea.post(f"/api/folder/{entry['id']}/copy").status_code == 404
    stayed = anna.get("/api/folder").json()["sheets"]
    assert [row["title"] for row in stayed] == ["Bleibt"]
    assert stayed[0]["author_name"] == "bea"
    assert stayed[0]["label"] == "Klasse 2"
    assert {row["title"] for row in bea.get("/api/sheets").json()} == {"Privat", "Bleibt"}


def test_the_sheet_stays_when_its_author_deletes_her_account():
    """The name stays when the account is gone. A school admin appointed later can still delete."""
    boss, anna, bea, school = seat_school()
    entry, _made = put(anna, "Von Anna", "Deutsch")
    assert anna.delete("/api/me").status_code == 200
    stayed = bea.get("/api/folder").json()["sheets"][0]
    assert stayed["title"] == "Von Anna"
    assert stayed["author_name"] == "anna"
    assert stayed["author_id"] is None
    assert bea.delete(f"/api/folder/{entry['id']}").status_code == 404
    cara = sign_in("cara@example.com")
    give_seat(boss, school["id"], "cara@example.com", admin=True)
    assert cara.delete(f"/api/folder/{entry['id']}").status_code == 200
    assert bea.get("/api/folder").json()["sheets"] == []


def test_another_school_sees_nothing():
    """No view across schools: a sheet, its page and a copy-out are missing there."""
    boss, anna, _bea, _school = seat_school()
    entry, _made = put(anna, "Nur hier", "Mathe")
    other = boss.post("/api/admin/schools", json={"name": "Andere"})
    assert other.status_code == 200, other.text
    cara = sign_in("cara@example.com")
    give_seat(boss, other.json()["id"], "cara@example.com", admin=True)
    assert cara.get("/api/folder").json()["school"]["name"] == "Andere"
    assert cara.get("/api/folder").json()["sheets"] == []
    assert cara.get(f"/api/folder/{entry['id']}").status_code == 404
    assert cara.delete(f"/api/folder/{entry['id']}").status_code == 404
    assert cara.post(f"/api/folder/{entry['id']}/copy").status_code == 404
    put(cara, "Drüben", "")
    assert titles(anna) == ["Nur hier"]
    assert titles(cara) == ["Drüben"]


def test_sort_and_search():
    """Sort by name, date and label. Search reads the title and the label, and nothing else."""
    _boss, anna, _bea, _school = seat_school()
    put(anna, "Zebra", "Mathe")
    put(anna, "apfel", "")
    put(anna, "Birne", "Klasse 2")
    assert titles(anna, sort="name") == ["apfel", "Birne", "Zebra"]
    assert titles(anna, sort="label") == ["apfel", "Birne", "Zebra"]
    assert titles(anna, sort="date") == ["Birne", "apfel", "Zebra"]
    assert titles(anna) == ["Birne", "apfel", "Zebra"]
    rows = {row["title"]: row for row in anna.get("/api/folder").json()["sheets"]}
    db.open_db().execute(
        "UPDATE folder_sheets SET updated = '2000-01-01 00:00:00' WHERE id = ?",
        (rows["Birne"]["id"],),
    )
    assert titles(anna, sort="date") == ["apfel", "Zebra", "Birne"]
    assert titles(anna, q="klasse") == ["Birne"]
    assert titles(anna, q="MATHE") == ["Zebra"]
    assert titles(anna, q="apf") == ["apfel"]
    assert titles(anna, q="anna") == []
    assert titles(anna, q="Hallo") == []
    assert anna.get("/api/folder", params={"sort": "nope"}).status_code == 422


def test_replace_keeps_the_author_and_the_label():
    """Replace writes a new copy of a sheet the caller owns. The name and the label stay."""
    boss, anna, bea, school = seat_school()
    cara = sign_in("cara@example.com")
    give_seat(boss, school["id"], "cara@example.com")
    entry, _made = put(bea, "Alt", "Mathe")
    fresh = sheet(bea, [box("a", "text", {**TEXT, "text": "neu"})], title="Neu")
    caras = sheet(cara, [box("a", "text", TEXT)], title="Fremd")
    annas = sheet(anna, [box("a", "text", TEXT)], title="Von der Leitung")
    db.open_db().execute(
        "UPDATE folder_sheets SET updated = '2000-01-01 00:00:00' WHERE id = ?",
        (entry["id"],),
    )
    # Not the author and not the admin: her own sheet does not open the entry.
    assert (
        cara.post(f"/api/folder/{entry['id']}/replace", json={"sheet_id": caras["id"]}).status_code
        == 404
    )
    # The admin does not get to copy a sheet she does not own.
    assert (
        anna.post(f"/api/folder/{entry['id']}/replace", json={"sheet_id": fresh["id"]}).status_code
        == 404
    )
    by_admin = anna.post(f"/api/folder/{entry['id']}/replace", json={"sheet_id": annas["id"]})
    assert by_admin.status_code == 200, by_admin.text
    assert by_admin.json()["sheet"]["title"] == "Von der Leitung"
    assert by_admin.json()["sheet"]["author_name"] == "bea"
    res = bea.post(f"/api/folder/{entry['id']}/replace", json={"sheet_id": fresh["id"]})
    assert res.status_code == 200, res.text
    replaced = res.json()["sheet"]
    assert replaced["title"] == "Neu"
    assert replaced["doc"] == fresh["doc"]
    assert replaced["label"] == "Mathe"
    assert replaced["author_name"] == "bea"
    assert replaced["created"] == entry["created"]
    assert replaced["updated"] > "2000-01-01 00:00:00"
    labelled = anna.patch(f"/api/folder/{entry['id']}", json={"label": "Klasse 2"})
    assert labelled.status_code == 200, labelled.text
    assert labelled.json()["sheet"]["label"] == "Klasse 2"
    assert (
        bea.patch(f"/api/folder/{entry['id']}", json={"label": "Deutsch"}).json()["sheet"]["label"]
        == "Deutsch"
    )
    assert cara.patch(f"/api/folder/{entry['id']}", json={"label": "x"}).status_code == 404


def test_pictures_are_copied_into_the_folder_and_out(data_dir):
    """A picture in the folder survives the author's file, and the copy out has its own."""
    boss, anna, bea, _school = seat_school()
    upload_id = upload(anna)
    made = sheet(anna, [picture(upload_id)], title="Mit Bild")
    entry = anna.post("/api/folder", json={"sheet_id": made["id"], "label": ""}).json()["sheet"]
    assert anna.get(f"/api/uploads/{upload_id}").content == png()
    user_id = anna.get("/api/me").json()["id"]
    (data_dir / "users" / str(user_id) / "uploads" / str(upload_id)).unlink()
    db.open_db().execute("DELETE FROM uploads WHERE id = ?", (upload_id,))
    assert bea.get(f"/api/uploads/{upload_id}").content == png()
    cara = sign_in("cara@example.com")
    other = boss.post("/api/admin/schools", json={"name": "Andere"}).json()
    give_seat(boss, other["id"], "cara@example.com")
    assert cara.get(f"/api/uploads/{upload_id}").status_code == 404
    copied = bea.post(f"/api/folder/{entry['id']}/copy").json()
    new_id = copied["doc"]["pages"][0]["blocks"][0]["props"]["upload"]
    assert new_id != upload_id
    assert bea.get(f"/api/uploads/{new_id}").content == png()
    assert anna.delete(f"/api/folder/{entry['id']}").status_code == 200
    assert bea.get(f"/api/uploads/{upload_id}").status_code == 404
    assert bea.get(f"/api/uploads/{new_id}").content == png()


def test_no_seat_and_no_session_have_no_folder():
    """No seat, no folder. Logged out, the folder is a login, and the site admin has no seat here."""
    guest = TestClient(app, base_url="https://testserver")
    assert guest.get("/api/folder").status_code == 401
    assert guest.post("/api/folder", json={"sheet_id": 1}).status_code == 401
    teacher = sign_in("a@example.com")
    assert teacher.get("/api/folder").status_code == 404
    assert teacher.post("/api/folder", json={"sheet_id": 1}).status_code == 404
    boss, _anna, _bea, _school = seat_school()
    assert boss.get("/api/folder").status_code == 404


def test_a_teacher_has_one_seat():
    """A teacher already seated stays there until the seat is removed. Only the site admin seats."""
    boss, anna, _bea, school = seat_school()
    other = boss.post("/api/admin/schools", json={"name": "Andere"})
    assert other.status_code == 200, other.text
    again = boss.post(
        f"/api/admin/schools/{other.json()['id']}/seats",
        json={"email": "Anna@example.com"},
    )
    assert again.status_code == 409
    missing = boss.post(
        f"/api/admin/schools/{school['id']}/seats",
        json={"email": "nobody@example.com"},
    )
    assert missing.status_code == 404
    assert anna.post("/api/admin/schools", json={"name": "Selbst"}).status_code == 404
    assert boss.post("/api/admin/schools", json={"name": "  "}).status_code == 422
    listed = boss.get("/api/admin/schools").json()
    assert {row["name"] for row in listed} == {"Waldschule", "Andere"}
    wald = next(row for row in listed if row["name"] == "Waldschule")
    assert {seat["email"]: seat["admin"] for seat in wald["seats"]} == {
        "anna@example.com": True,
        "bea@example.com": False,
    }


def test_the_folder_tab_puts_a_copy_in_and_takes_one_out(window, server):
    """#93: the sheet list shows the folder as a second tab, and a copy comes back as her sheet."""
    page, client = window()
    me = client.get("/api/me").json()
    boss = sign_in("admin@example.com", admin=True)
    made = boss.post("/api/admin/schools", json={"name": "Waldschule"})
    assert made.status_code == 200, made.text
    give_seat(boss, made.json()["id"], me["email"])
    sheet(client, [box("a", "text", TEXT)], title="Plusaufgaben")
    page.goto(server)
    expect(page.get_by_role("tab", name="Schulordner")).to_be_visible()
    page.once("dialog", lambda dialog: dialog.accept("Klasse 2"))
    page.get_by_role("button", name="Plusaufgaben in den Schulordner").click()
    expect(page.get_by_role("heading", name="Schulordner")).to_be_visible()
    expect(page.get_by_text("Klasse 2")).to_be_visible()
    expect(page.get_by_text(me["email"].split("@")[0])).to_be_visible()
    page.get_by_role("link", name=re.compile("Plusaufgaben")).click()
    expect(page.get_by_role("heading", name="Plusaufgaben")).to_be_visible()
    expect(page.get_by_text("Nur ansehen")).to_be_visible()
    page.get_by_role("button", name="Kopie in meine Blätter").click()
    expect(page).to_have_url(re.compile(r"/blatt/\d+$"))
    titles = [row["title"] for row in client.get("/api/sheets").json()]
    assert "Kopie von Plusaufgaben" in titles
