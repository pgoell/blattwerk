"""Sheets, templates and uploads belong to one user, and a stale save is refused."""

import re

from fastapi.testclient import TestClient
from test_app import (
    EMPTY,
    PASSWORD,
    TABLES,
    invite,
    kinds,
    my_id,
    own,
    user,
)
from ui import png

from blattwerk import (
    auth,
    db,
)
from blattwerk.app import app


def test_every_answer_about_a_sheet_names_the_user_it_was_served_for():
    """Issue #353, A4: `user_id` in a sheet, and `X-User` beside the 404 of a sheet that is
    another teacher's or not there."""
    a, b = user("a@example.com"), user("b@example.com")
    made = a.post("/api/sheets", json={"title": "Meins", "doc": EMPTY}).json()
    path = f"/api/sheets/{made['id']}"
    save = {"doc": {**EMPTY, "pages": []}, "version": made["version"]}
    answers = [
        made,
        a.get(path).json(),
        a.get("/api/sheets").json()[0],
        a.patch(path, json=save).json(),
        a.patch(path, json={"title": "Neu"}).json(),
        a.post(f"{path}/duplicate").json(),
    ]
    assert [sheet["user_id"] for sheet in answers] == [my_id(a)] * 6
    asks = [("GET", path), ("PATCH", path), ("DELETE", path), ("POST", f"{path}/duplicate")]
    for client, at in ((b, path), (a, "/api/sheets/99")):
        for method, to in asks:
            res = client.request(method, to.replace(path, at), json=save)
            assert res.status_code == 404, (method, to)
            assert res.headers["X-User"] == str(my_id(client))
        assert client.get(f"{at}/pdf").headers["X-User"] == str(my_id(client))


def test_new_account_inherits_nothing_from_a_deleted_one(data_dir):
    a = user("a@example.com")
    a_id = my_id(a)
    a.post("/api/sheets", json={"title": "Meins", "doc": EMPTY})
    a.post("/api/templates", json={"name": "Meins", "doc": EMPTY})
    upload = a.post("/api/uploads", files={"file": ("bild", png(), "image/png")}).json()["id"]
    a.post("/api/feedback", data={"text": "x"})
    con = db.open_db()
    reset = auth.new_link(con, a_id)
    early = invite()
    cookie = a.cookies["session"]
    assert a.delete("/api/me").status_code == 200

    stale = TestClient(app, base_url="https://testserver", cookies={"session": cookie})
    assert stale.get("/api/me").status_code == 401
    b = user("b@example.com")
    b_id = my_id(b)
    assert b_id != a_id
    assert b.get("/api/sheets").json() == []
    assert own(b) == []
    assert b.get(f"/api/uploads/{upload}").status_code == 404
    assert not (data_dir / "users" / str(b_id)).exists()
    assert not (data_dir / "users" / str(a_id)).exists()
    assert stale.get("/api/me").status_code == 401
    # Nothing of A is left for a later account to own: no row, no session, no link.
    for table in TABLES[1:]:
        count = f"SELECT count(*) FROM {table} WHERE user_id = ?"
        assert con.execute(count, (a_id,)).fetchone()[0] == 0, table
    # A's reset link is dead, and B's password stays B's.
    new = {"token": reset, "password": "ganz-neu-geheim"}
    assert stale.post("/api/reset", json=new).status_code == 404
    login = {"email": "b@example.com", "password": PASSWORD}
    assert stale.post("/api/login", json=login).status_code == 200
    # An invite made before the delete is no one's: it opens a new account, not A's.
    c = TestClient(app, base_url="https://testserver")
    body = {"token": early, "email": "c@example.com", "password": PASSWORD}
    assert c.post("/api/signup", json=body).json()["id"] not in (a_id, b_id)
    assert c.get("/api/sheets").json() == []


def test_leftover_folder_never_reaches_a_later_account(data_dir, monkeypatch):
    a = user("a@example.com")
    a.post("/api/uploads", files={"file": ("bild", png(), "image/png")})
    a.post("/api/feedback", data={"text": "x"})
    # The delete of the folder fails, as on a full or read-only disk.
    monkeypatch.setattr(auth.shutil, "rmtree", lambda *args, **kwargs: None)
    assert a.delete("/api/me").status_code == 200
    left = data_dir / "users" / "1"
    files = sorted(left.rglob("*"))
    assert len(files) == 5

    b = user("b@example.com")
    assert my_id(b) == 2
    upload = b.post("/api/uploads", files={"file": ("bild", png(), "image/png")}).json()["id"]
    stamp = b.post("/api/feedback", data={"text": "y"}).json()["saved"]
    assert (data_dir / "users" / "2" / "uploads" / str(upload)).is_file()
    assert (data_dir / "users" / "2" / "feedback" / stamp).is_dir()
    assert sorted(left.rglob("*")) == files


def test_deleting_an_account_ends_every_session_and_open_link():
    first = user("a@example.com")
    second = TestClient(app, base_url="https://testserver")
    login = {"email": "a@example.com", "password": PASSWORD}
    assert second.post("/api/login", json=login).status_code == 200
    reset = auth.new_link(db.open_db(), my_id(first))
    assert first.delete("/api/me").status_code == 200
    assert second.get("/api/me").status_code == 401
    assert second.post("/api/sheets", json={"title": "x", "doc": EMPTY}).status_code == 401
    new = {"token": reset, "password": "ganz-neu-geheim"}
    assert second.post("/api/reset", json=new).status_code == 404
    assert db.open_db().execute("SELECT count(*) FROM links").fetchone()[0] == 0


def test_built_in_templates_are_everyones_and_stay():
    client = user("a@example.com")
    other = user("b@example.com")
    built_in = client.get("/api/templates").json()
    assert other.get("/api/templates").json() == built_in
    assert [t["name"] for t in built_in] == [
        "Arbeitsblatt",
        "Klassenarbeit",
        "Beschriftungsblatt",
        "Wochenplan",
        "Elternbrief",
        "Rechenblatt Klasse 1",
        "Rechenblatt Klasse 2",
        "Rechenblatt Klasse 3",
        "Rechenblatt Klasse 4",
        "Schreibblatt Lineatur 1",
        "Schreibblatt Lineatur 2",
        "Lernwörter",
        "Klassenarbeit Deckblatt",
    ]
    for t in built_in:
        assert client.delete(f"/api/templates/{t['id']}").status_code == 404
    assert client.get("/api/templates").json() == built_in

    for t in built_in:
        assert t["group"] in {"Allgemein", "Mathe", "Deutsch", "Organisation"}
        if t["id"] < -3 and t["name"] != "Elternbrief":
            assert t["doc"]["pages"][0]["blocks"][0]["type"] == "name"
        blocks = [b for page in t["doc"]["pages"] for b in page["blocks"]]
        # A start point: every block can move, and each has its own id.
        assert not any(b["locked"] for b in blocks)
        assert len({b["id"] for b in blocks}) == len(blocks)
        # Everything lies on the page.
        assert all(0 <= b["x"] <= b["x"] + b["w"] <= 210 for b in blocks)
        assert all(0 <= b["y"] <= b["y"] + b["h"] <= 297 for b in blocks)

    sheet, test, labels = (t["doc"]["pages"] for t in built_in[:3])
    # The name, the title and two empty areas.
    assert [kinds(page) for page in sheet] == [["name", "text", "rounded", "rounded"]]
    # Three pages, each with the name, the points total and numbered tasks with their points.
    assert len(test) == 3
    for page in test:
        assert kinds(page)[:2] == ["name", "points"]
        tasks = [b for b in page["blocks"] if b.get("mark") == "1."]
        assert tasks
        assert kinds(page).count("points") == 1 + len(tasks)
    # The title, the picture's area and lines with arrows to label it.
    assert [kinds(page)[:2] for page in labels] == [["text", "rect"]]
    assert kinds(labels[0]).count("line") == kinds(labels[0]).count("arrow") == 6


def test_templates_belong_to_one_user():
    client = user("a@example.com")
    other = user("b@example.com")
    doc = {"blocks": [], "guides": {"x": [70], "y": []}, "grid": 5}
    saved = client.post("/api/templates", json={"name": "Drei Spalten", "doc": doc}).json()
    assert own(client) == [{**saved, "name": "Drei Spalten", "doc": doc}]
    assert own(other) == []
    assert other.delete(f"/api/templates/{saved['id']}").status_code == 404
    assert client.delete(f"/api/templates/{saved['id']}").status_code == 200
    assert own(client) == []
    assert client.post("/api/templates", json={"name": "", "doc": doc}).status_code == 422


def test_sheets_belong_to_one_user():
    client = user("a@example.com")
    other = user("b@example.com")
    doc = {"pages": [{"blocks": []}], "guides": {"x": [], "y": []}, "grid": 0}
    sheet = client.post("/api/sheets", json={"title": "Plusaufgaben", "doc": doc}).json()
    url = f"/api/sheets/{sheet['id']}"
    assert sheet["title"] == "Plusaufgaben"
    assert sheet["doc"] == doc
    assert client.get(url).json() == sheet
    assert client.get("/api/sheets").json() == [sheet]

    # A save may bring the title, the document or both.
    grid = {**doc, "grid": 5}
    assert client.patch(url, json={"title": "Minusaufgaben"}).json()["doc"] == doc
    assert client.patch(url, json={"doc": grid, "version": 1}).json()["title"] == "Minusaufgaben"
    assert client.patch(url, json={"title": ""}).status_code == 422
    copy = client.post(f"{url}/duplicate").json()
    assert copy["id"] != sheet["id"]
    assert copy["title"] == "Minusaufgaben (Kopie)"
    assert copy["doc"] == grid
    assert {s["id"] for s in client.get("/api/sheets").json()} == {sheet["id"], copy["id"]}

    assert other.get("/api/sheets").json() == []
    assert other.get(url).status_code == 404
    assert other.patch(url, json={"title": "Geklaut"}).status_code == 404
    # Not a 409 either: that would tell a stranger the sheet is there.
    assert other.patch(url, json={"doc": doc, "version": 1}).status_code == 404
    assert other.patch(url, json={"doc": doc, "version": 2}).status_code == 404
    assert other.post(f"{url}/duplicate").status_code == 404
    assert other.delete(url).status_code == 404
    assert client.get(url).json()["title"] == "Minusaufgaben"

    assert client.delete(url).status_code == 200
    assert client.get(url).status_code == 404
    assert [s["id"] for s in client.get("/api/sheets").json()] == [copy["id"]]


def test_every_call_for_an_item_hides_other_users_items():
    """Walks the routes, so a new call for an item is checked without a new test."""
    client = user("a@example.com")
    other = user("b@example.com")
    sheet = client.post("/api/sheets", json={"title": "Meins", "doc": EMPTY}).json()
    template = client.post("/api/templates", json={"name": "Meins", "doc": EMPTY}).json()
    # Every id is 1, the first user's included, so one path fits every route.
    assert sheet["id"] == template["id"] == client.get("/api/me").json()["id"] == 1

    calls = [
        (method, re.sub(r"{\w+}", "1", path))
        for path, methods in app.openapi()["paths"].items()
        if path.startswith("/api/") and "{" in path
        for method in methods
    ]
    assert len(calls) >= 8
    for method, path in calls:
        assert other.request(method, path, json={}).status_code == 404, (method, path)

    assert client.get("/api/sheets").json() == [sheet]
    assert own(client) == [template]
    assert other.get("/api/sheets").json() == []
    assert own(other) == []


def test_stale_save_gets_409():
    client = user("a@example.com")
    doc = {"pages": [{"blocks": []}], "guides": {"x": [], "y": []}, "grid": 0}
    sheet = client.post("/api/sheets", json={"title": "Blatt", "doc": doc}).json()
    url = f"/api/sheets/{sheet['id']}"
    assert sheet["version"] == 1

    # A rename brings no document: it needs no version and leaves the version alone.
    assert client.patch(url, json={"title": "Umbenannt"}).json()["version"] == 1
    five = client.patch(url, json={"doc": {**doc, "grid": 5}, "version": 1}).json()
    assert five["version"] == 2
    assert five["title"] == "Umbenannt"

    # Another device still holds version 1.
    stale = {"title": "Veraltet", "doc": {**doc, "grid": 10}, "version": 1}
    assert client.patch(url, json=stale).status_code == 409
    assert client.get(url).json() == five
    assert client.patch(url, json={**stale, "version": 2}).json()["version"] == 3
    # A document with no version is turned down.
    assert client.patch(url, json={"doc": {**doc, "grid": 20}}).status_code == 422
    assert client.get(url).json()["doc"]["grid"] == 10
    # To overwrite, the stale device asks for the version first.
    forced = client.patch(url, json={**stale, "version": client.get(url).json()["version"]}).json()
    assert forced["version"] == 4
    assert forced["title"] == "Veraltet"
    assert client.post(f"{url}/duplicate").json()["version"] == 1
