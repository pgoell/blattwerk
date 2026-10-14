"""The Vorlagen panel: built-in templates in groups with a thumbnail, and what applying keeps."""

import time

from playwright.sync_api import expect
from ui import TEXT, at, box, doc, maths, reload, user

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
GROUPS = ["Allgemein", "Mathe", "Deutsch", "Organisation"]


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


def seed(page, client, kind):
    """The seed of the page's first block of that kind, as the server holds the sheet now."""
    blocks = client.get(f"/api/sheets/{page.url.rsplit('/', 1)[1]}").json()["doc"]["pages"][0][
        "blocks"
    ]
    return next((b["props"]["seed"] for b in blocks if b["type"] == kind), None)


def until_not(read, old, seconds=5):
    """Reads until the value is not `old` any more, as the saved sheet takes the change."""
    deadline = time.time() + seconds
    value = read()
    while value == old and time.time() < deadline:
        time.sleep(0.1)
        value = read()
    assert value != old
    return value


def open_panel(page):
    page.get_by_role("tab", name="Vorlagen").click()
    expect(page.get_by_role("heading", name="Vorlagen", exact=True)).to_be_visible()


def apply(page, name):
    page.locator(".tpl button", has_text=name).click()


def test_panel_groups_the_builtin_templates_under_headings(editor):
    page = editor(box("a", "text", TEXT))
    open_panel(page)
    for group in ["Allgemein", "Organisation"]:
        heading = page.get_by_role("heading", name=group, exact=True)
        expect(heading).to_be_visible()
        expect(page.get_by_role("group", name=group).locator(".tpl button").first).to_be_visible()


def test_each_builtin_template_button_shows_a_paper_thumbnail(editor):
    page = editor(box("a", "text", TEXT))
    open_panel(page)
    buttons = page.locator(".tpl button")
    expect(buttons.first).to_be_visible()
    for i in range(buttons.count()):
        assert buttons.nth(i).locator("svg").count() >= 1


def test_groups_are_in_the_order_of_the_contract(editor):
    page = editor(box("a", "text", TEXT))
    open_panel(page)
    expect(page.get_by_role("heading", name="Allgemein", exact=True)).to_be_visible()
    names = page.locator("aside.left h3, aside.left h2").all_inner_texts()
    shown = [n for n in names if n in GROUPS]
    assert shown == [g for g in GROUPS if g in shown]


def test_applying_a_stubbed_mathe_template_twice_reseeds_each_time(editor, server):
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    stub(page, stub_template(client))
    reload(page, page.url)
    open_panel(page)
    apply(page, "Mathe-Stub")
    first = until_not(lambda: seed(page, client, "zahlenmauer"), 1)
    first_maths = until_not(lambda: seed(page, client, "maths"), 7)
    apply(page, "Mathe-Stub")
    until_not(lambda: seed(page, client, "zahlenmauer"), first)
    until_not(lambda: seed(page, client, "maths"), first_maths)


def test_one_undo_takes_back_a_whole_template_with_its_maths(editor):
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    stub(page, stub_template(client))
    reload(page, page.url)
    open_panel(page)
    apply(page, "Mathe-Stub")
    expect(at(page, "z")).to_be_visible()
    page.keyboard.press("Control+z")
    expect(at(page, "a")).to_be_visible()
    expect(at(page, "z")).to_have_count(0)
    expect(at(page, "m")).to_have_count(0)


def test_maths_failure_keeps_the_template_exercises(editor):
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    stub(page, stub_template(client))
    reload(page, page.url)
    page.route("**/api/maths", lambda route: route.fulfill(status=500, body="nein"))
    open_panel(page)
    apply(page, "Mathe-Stub")
    until_not(lambda: seed(page, client, "zahlenmauer"), None)
    assert seed(page, client, "maths") == 7


def test_applying_a_template_keeps_the_sheets_words(editor):
    client = user()
    page = editor(box("a", "text", TEXT), client=client, words=["Hund", "Katze"])
    stub(page, stub_template(client))
    reload(page, page.url)
    open_panel(page)
    apply(page, "Mathe-Stub")
    expect(at(page, "z")).to_be_visible()
    assert doc(page, client)["words"] == ["Hund", "Katze"]


def test_own_template_applies_with_its_seed_unchanged(editor):
    client = user()
    own = {
        "pages": [{"blocks": [box("z", "zahlenmauer", ZAHL)]}],
        "guides": {"x": [], "y": []},
        "grid": 0,
    }
    client.post("/api/templates", json={"name": "Eigene", "doc": own})
    page = editor(box("a", "text", TEXT), client=client)
    reload(page, page.url)
    open_panel(page)
    apply(page, "Eigene")
    blocks = doc(page, client)["pages"][0]["blocks"]
    assert next(b for b in blocks if b["type"] == "zahlenmauer")["props"]["seed"] == 1


def test_enter_on_a_template_button_applies_it(editor):
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    stub(page, stub_template(client, name="Enter-Stub", group="Deutsch"))
    reload(page, page.url)
    open_panel(page)
    page.locator(".tpl button", has_text="Enter-Stub").focus()
    page.keyboard.press("Enter")
    expect(at(page, "z")).to_be_visible()
    expect(
        page.get_by_role("group", name="Deutsch").locator(".tpl button", has_text="Enter-Stub")
    ).to_be_visible()


def test_saving_an_own_template_keeps_the_groups(editor):
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    open_panel(page)
    page.get_by_label("Name der Vorlage").fill("Meine Neue")
    page.get_by_role("button", name="Dieses Blatt als Vorlage").click()
    expect(page.locator(".tpl button", has_text="Meine Neue")).to_be_visible()
    expect(page.get_by_role("heading", name="Allgemein", exact=True)).to_be_visible()
    expect(page.get_by_role("heading", name="Meine Vorlagen", exact=True)).to_be_visible()
