"""A sheet posted through the API may lack its guides and grid, or hold them broken.

It still opens, prints and lists, and a save keeps its blocks and words (#634).
"""

import pytest
from conftest import MEASURED
from playwright.sync_api import expect
from ui import TEXT, at, box, doc, pick, user

from blattwerk import pdf

TITLE = "Ohne Hilfslinien"


def raw(client, guides=..., grid=...):
    """A sheet posted as it is: one text block, the words, and only the guides and grid given."""
    body = {"pages": [{"blocks": [box("a", "text", TEXT)]}], "words": ["Hallo"]}
    if guides is not ...:
        body["guides"] = guides
    if grid is not ...:
        body["grid"] = grid
    return client.post("/api/sheets", json={"title": TITLE, "doc": body}).json()["id"]


@pytest.fixture
def opened(browser, server):
    """Opens a sheet in the editor, as its user, and gives the page. Closes what it opened."""
    contexts = []

    def start(client, sheet_id):
        context = browser.new_context(viewport={"width": 1400, "height": 1000})
        contexts.append(context)
        session = {"name": "session", "value": client.cookies["session"], "url": server}
        context.add_cookies([session])
        context.add_init_script("window.saveAfter = 1100")
        context.add_init_script("localStorage.setItem('tour', '1')")
        page = context.new_page()
        page.goto(f"{server}/blatt/{sheet_id}")
        expect(page.locator('main.editor[data-ready="1"]')).to_be_visible(timeout=10000)
        page.wait_for_function(MEASURED, timeout=10000)
        return page

    yield start
    for context in contexts:
        context.close()


def test_a_sheet_with_no_guides_opens_in_the_editor_and_keeps_all(opened):
    client = user()
    page = opened(client, raw(client))
    expect(page.get_by_label("Titel", exact=True)).to_have_value(TITLE)
    expect(at(page, "a")).to_contain_text("Hallo")
    pick(page, "a")
    page.keyboard.press("ArrowDown")
    stored = doc(page, client)
    assert stored["pages"][0]["blocks"][0]["id"] == "a"
    assert stored["pages"][0]["blocks"][0]["props"]["text"] == "Hallo"
    assert stored["words"] == ["Hallo"]
    assert stored["guides"] == {"x": [], "y": []}


@pytest.mark.parametrize("guides", [None, {"x": [10]}, "x"], ids=["null", "no-y", "text"])
def test_a_sheet_with_broken_guides_opens(opened, guides):
    client = user()
    page = opened(client, raw(client, guides=guides, grid=0))
    expect(at(page, "a")).to_contain_text("Hallo")


def test_print_and_thumbnail_draw_a_sheet_with_no_guides(browser, server):
    client = user()
    mine = raw(client)
    context = browser.new_context()
    context.add_cookies([{"name": "session", "value": client.cookies["session"], "url": server}])
    context.add_init_script("localStorage.setItem('tour', '1')")
    page = context.new_page()
    page.set_extra_http_headers({"X-Render-Token": pdf.new_token(mine)})
    page.goto(f"{server}/druck/{mine}")
    page.wait_for_selector("body.ready", state="attached")
    expect(page.locator("body")).to_contain_text("Hallo")
    page.set_extra_http_headers({})
    page.goto(server)
    expect(page.locator(".sheets li .paper")).to_contain_text("Hallo")
    context.close()
