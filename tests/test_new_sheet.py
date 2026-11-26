"""#1184: "Neues Blatt" opens a chooser with the templates."""

import itertools
import re

from playwright.sync_api import expect
from test_loading import window  # noqa: F401
from ui import TEXT, at, box
from ui_new import EMPTY, card, chooser, new_sheet

FILTERS = ["Alle", "Mathe", "Deutsch", "Meine Vorlagen"]
OWN = {
    "pages": [{"blocks": [box("eigen", "text", {**TEXT, "text": "Aus meiner Vorlage"})]}],
    "guides": {"x": [], "y": []},
    "grid": 0,
}


def listed(window, server, own=False):  # noqa: F811
    page, client = window()
    if own:
        assert client.post("/api/templates", json={"name": "Meine Eigene", "doc": OWN}).is_success
    page.goto(server)
    return page, client


def names(shelf):
    return [name.strip() for name in shelf.locator(".tile > span:not(.pic)").all_inner_texts()]


def sheet_of(page, client):
    """The sheet the editor opened, as the server holds it."""
    page.wait_for_url(re.compile(r"/blatt/\d+$"))
    return client.get(f"/api/sheets/{page.url.rsplit('/', 1)[1]}").json()


def test_the_chooser_shows_the_empty_sheet_first_and_each_template_with_a_picture(window, server):  # noqa: F811
    page, client = listed(window, server, own=True)
    templates = client.get("/api/templates").json()
    shelf = chooser(page)
    expect(shelf.get_by_role("heading", name="Neues Blatt")).to_be_visible()
    expect(shelf.locator(".tile")).to_have_count(len(templates) + 1)
    assert names(shelf) == [EMPTY, *(t["name"] for t in templates)]
    # Each template shows its first page drawn small, and the empty sheet a white page.
    expect(shelf.locator(".tile .pic .paper")).to_have_count(len(templates))
    expect(card(shelf).locator(".pic.blank")).to_be_visible()
    picture = card(shelf, "Wochenplan").locator(".pic").bounding_box()
    assert picture["width"] > 100 and picture["height"] > 60
    # No card lies over the next: each stands in a row of its own height.
    boxes = [tile.bounding_box() for tile in shelf.locator(".tile").all()]
    for one, two in itertools.pairwise(boxes):
        beside = two["y"] == one["y"] and two["x"] >= one["x"] + one["width"]
        assert beside or two["y"] >= one["y"] + one["height"]


def test_the_filters_show_mathe_deutsch_and_the_teachers_own(window, server):  # noqa: F811
    page, client = listed(window, server, own=True)
    built_in = [t for t in client.get("/api/templates").json() if t["id"] < 0]
    shelf = chooser(page)
    filters = shelf.get_by_role("group", name="Vorlagen zeigen")
    expect(filters.get_by_role("button")).to_have_text(FILTERS)
    expect(filters.get_by_role("button", name="Alle")).to_have_attribute("aria-pressed", "true")
    for group in ("Mathe", "Deutsch"):
        filters.get_by_role("button", name=group, exact=True).click()
        assert names(shelf) == [t["name"] for t in built_in if t["group"] == group]
    filters.get_by_role("button", name="Meine Vorlagen").click()
    assert names(shelf) == ["Meine Eigene"]
    filters.get_by_role("button", name="Alle").click()
    expect(card(shelf)).to_be_visible()


def test_meine_vorlagen_says_so_where_the_teacher_has_none(window, server):  # noqa: F811
    page, _ = listed(window, server)
    shelf = chooser(page)
    shelf.get_by_role("button", name="Meine Vorlagen").click()
    expect(shelf.locator(".tile")).to_have_count(0)
    expect(shelf).to_contain_text("Noch keine eigene Vorlage.")


def test_the_empty_sheet_opens_an_empty_sheet(window, server):  # noqa: F811
    page, client = listed(window, server)
    new_sheet(page)
    made = sheet_of(page, client)
    assert made["title"] == "Unbenanntes Blatt"
    assert [len(p["blocks"]) for p in made["doc"]["pages"]] == [0]


def test_a_sheet_made_from_a_template_takes_the_templates_name(window, server):  # noqa: F811
    page, client = listed(window, server, own=True)
    new_sheet(page, "Wochenplan")
    made = sheet_of(page, client)
    assert made["title"] == "Wochenplan"
    assert made["doc"]["pages"][0]["blocks"]
    expect(page.get_by_label("Titel", exact=True)).to_have_value("Wochenplan")

    page.goto(server)
    new_sheet(page, "Meine Eigene")
    made = sheet_of(page, client)
    assert made["title"] == "Meine Eigene"
    expect(at(page, "eigen")).to_contain_text("Aus meiner Vorlage")


def test_a_built_in_maths_template_starts_with_exercises_of_its_own(window, server):  # noqa: F811
    """As in the editor's panel: a built-in template gets fresh seeds, so two sheets differ."""
    page, client = listed(window, server)
    seeds = []
    for _ in range(2):
        page.goto(server)
        new_sheet(page, "Rechenblatt Klasse 2")
        blocks = sheet_of(page, client)["doc"]["pages"][0]["blocks"]
        seeds.append([b["props"]["seed"] for b in blocks if "seed" in b["props"]])
    assert seeds[0] and seeds[0] != seeds[1]


def test_escape_and_abbrechen_shut_the_chooser_and_make_no_sheet(window, server):  # noqa: F811
    page, client = listed(window, server)
    button = page.get_by_role("button", name="Neues Blatt", exact=True)
    shelf = chooser(page)
    page.keyboard.press("Escape")
    expect(shelf).to_have_count(0)
    expect(button).to_be_focused()
    shelf = chooser(page)
    shelf.get_by_role("button", name="Abbrechen").click()
    expect(shelf).to_have_count(0)
    assert client.get("/api/sheets").json() == []


def test_the_chooser_still_gives_an_empty_sheet_when_the_templates_do_not_load(window, server):  # noqa: F811
    page, client = listed(window, server)
    page.route("**/api/templates", lambda route: route.fulfill(status=500))
    shelf = chooser(page)
    expect(shelf.get_by_role("alert")).to_contain_text("Die Vorlagen konnten nicht geladen werden.")
    card(shelf).click()
    assert sheet_of(page, client)["title"] == "Unbenanntes Blatt"


def test_an_own_template_that_cannot_be_deleted_stays_and_the_chooser_says_so(window, server):  # noqa: F811
    page, _ = listed(window, server, own=True)
    shelf = chooser(page)
    page.on("dialog", lambda asked: asked.accept())
    page.route(re.compile(r"/api/templates/\d+$"), lambda route: route.fulfill(status=500))
    shelf.get_by_label("Vorlage Meine Eigene löschen").click()
    said = "Die Vorlage „Meine Eigene“ konnte nicht gelöscht werden. Versuch es gleich noch einmal."
    expect(shelf.get_by_role("alert")).to_have_text(said)
    expect(card(shelf, "Meine Eigene")).to_be_visible()
    page.unroute(re.compile(r"/api/templates/\d+$"))
    shelf.get_by_label("Vorlage Meine Eigene löschen").click()
    expect(card(shelf, "Meine Eigene")).to_have_count(0)
    expect(shelf.get_by_role("alert")).to_have_count(0)
