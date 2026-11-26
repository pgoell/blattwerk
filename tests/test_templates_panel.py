"""A sheet made from a template under "Neues Blatt": fresh numbers for a built-in one, and the
sheet stored as a template of the teacher's own."""

import time

from playwright.sync_api import expect
from ui import TEXT, at, blatt, box, doc, maths, user
from ui_new import card, chooser, from_template

ZAHL = {
    "base": 3,
    "count": 4,
    "columns": 2,
    "max": 20,
    "op": "+",
    "given": "base",
    "empty": False,
    "seed": 1,
}


def stub_template(client, name="Mathe-Stub", group="Mathe", words=False):
    """A built-in-like template: a zahlenmauer with seed 1 and a maths block with seed 7."""
    doc_ = {
        "pages": [{"blocks": [box("z", "zahlenmauer", ZAHL), box("m", "maths", maths(client))]}],
        "guides": {"x": [], "y": []},
        "grid": 0,
    }
    if words:
        doc_["words"] = ["Stern"]
    return {"id": -99, "name": name, "group": group, "doc": doc_}


def stub(page, *extra):
    """The templates the server gives, and `extra` after them. Takes effect at the next load."""

    def answer(route):
        listed = route.fetch().json()
        route.fulfill(json=[*listed, *extra])

    page.route("**/api/templates", answer)


def saved_blocks(page, client):
    """The first page's blocks as the server holds the sheet now."""
    return client.get(f"/api/sheets/{page.url.rsplit('/', 1)[1]}").json()["doc"]["pages"][0][
        "blocks"
    ]


def seed(page, client, kind):
    """The seed of the page's first block of that kind, as the server holds the sheet now."""
    return next((b["props"]["seed"] for b in saved_blocks(page, client) if b["type"] == kind), None)


def height(page, client, kind):
    """The height of the page's first block of that kind, as the server holds the sheet now."""
    return next((b["h"] for b in saved_blocks(page, client) if b["type"] == kind), None)


def until_not(read, old, seconds=5):
    """Reads until the value is not `old` any more, as the saved sheet takes the change."""
    deadline = time.time() + seconds
    value = read()
    while value == old and time.time() < deadline:
        time.sleep(0.1)
        value = read()
    assert value != old
    return value


def test_two_sheets_from_a_stubbed_mathe_template_have_seeds_of_their_own(editor, server):
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    stub(page, stub_template(client))
    from_template(page, "Mathe-Stub")
    first = until_not(lambda: seed(page, client, "zahlenmauer"), 1)
    first_maths = until_not(lambda: seed(page, client, "maths"), 7)
    from_template(page, "Mathe-Stub")
    assert seed(page, client, "zahlenmauer") not in (1, first)
    assert seed(page, client, "maths") not in (7, first_maths)


def test_maths_failure_keeps_the_template_exercises(editor):
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    stub(page, stub_template(client))
    page.route("**/api/maths", lambda route: route.fulfill(status=500, body="nein"))
    from_template(page, "Mathe-Stub")
    until_not(lambda: seed(page, client, "zahlenmauer"), None)
    assert seed(page, client, "maths") == 7


def test_a_template_brings_its_words(editor):
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    stub(page, stub_template(client, words=True))
    from_template(page, "Mathe-Stub")
    expect(at(page, "z")).to_be_visible()
    assert doc(page, client)["words"] == ["Stern"]


def test_own_template_gives_a_sheet_with_its_seed_unchanged(editor):
    client = user()
    own = {
        "pages": [{"blocks": [box("z", "zahlenmauer", ZAHL)]}],
        "guides": {"x": [], "y": []},
        "grid": 0,
    }
    client.post("/api/templates", json={"name": "Eigene", "doc": own})
    page = editor(box("a", "text", TEXT), client=client)
    from_template(page, "Eigene")
    blocks = doc(page, client)["pages"][0]["blocks"]
    assert next(b for b in blocks if b["type"] == "zahlenmauer")["props"]["seed"] == 1


def test_a_sheet_stored_as_a_template_stands_under_neues_blatt(editor):
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    blatt(page)
    page.get_by_label("Name der Vorlage").fill("Meine Neue")
    page.get_by_role("button", name="Als Vorlage speichern").click()
    said = "„Meine Neue“ ist gespeichert. Du findest die Vorlage unter „Neues Blatt“."
    expect(page.locator(".panel [role=status]")).to_have_text(said)
    expect(page.get_by_label("Name der Vorlage")).to_have_value("")
    page.goto(page.url.split("/blatt/")[0] + "/")
    shelf = chooser(page)
    shelf.get_by_role("button", name="Meine Vorlagen").click()
    expect(card(shelf, "Meine Neue")).to_be_visible()


def test_an_own_template_is_deleted_under_neues_blatt(editor):
    client = user()
    own = {"pages": [{"blocks": [box("a", "text", TEXT)]}], "guides": {"x": [], "y": []}, "grid": 0}
    client.post("/api/templates", json={"name": "Alt", "doc": own})
    page = editor(box("a", "text", TEXT), client=client)
    page.goto(page.url.split("/blatt/")[0] + "/")
    shelf = chooser(page)
    asked = []
    page.once("dialog", lambda box_: (asked.append(box_.message), box_.accept()))
    shelf.get_by_label("Vorlage Alt löschen").click()
    expect(card(shelf, "Alt")).to_have_count(0)
    assert asked == ["Vorlage „Alt“ löschen?"]
    assert [t for t in client.get("/api/templates").json() if t["id"] > 0] == []
    # The built-in ones have no such button.
    expect(shelf.get_by_label("Vorlage Wochenplan löschen")).to_have_count(0)


def test_a_maths_block_grows_to_fit_its_fresh_exercises(editor):
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    tall = {
        "id": -99,
        "name": "Mathe-Hoch",
        "group": "Mathe",
        "doc": {
            "pages": [{"blocks": [box("m", "maths", maths(client, count=12), h=10)]}],
            "guides": {"x": [], "y": []},
            "grid": 0,
        },
    }
    stub(page, tall)
    from_template(page, "Mathe-Hoch")
    until_not(lambda: height(page, client, "maths"), None)
    grown = until_not(lambda: height(page, client, "maths"), 10)
    assert grown > 10
    # Every exercise's grid lies inside the block: the written part is not cut off.
    grid = at(page, "m").locator(".maths")
    expect(grid).to_be_visible()
    fits = grid.evaluate("e => e.scrollHeight <= e.clientHeight + 1")
    assert fits
