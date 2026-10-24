"""The Lernwörter-Blatt is a new page, and a long list runs on to more pages."""
# The fixtures imported below are named again as a test's arguments.
# ruff: noqa: F811

import re

from playwright.sync_api import expect
from test_words import (
    editor,  # noqa: F401
    list_tab,
    redo,
    store_words,
    undo,
)
from ui import (
    TEXT,
    box,
    doc,
    user,
)


def test_the_lernwoerter_blatt_is_a_new_page_in_one_step(editor):
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    store_words(page, client, ["Hund", "Katze", "Igel"])
    list_tab(page)
    page.get_by_role("button", name="Lernwörter-Blatt").click()
    stored = doc(page, client)
    assert len(stored["pages"]) == 2
    blatt = stored["pages"][1]["blocks"]
    assert [b["type"] for b in blatt] == ["text", "name", "ruling", "ruling", "ruling"]
    assert blatt[0]["props"]["text"] == "Lernwörter"
    lines = blatt[2:]
    assert [b["props"]["list"] for b in lines] == ["copy", "trace", "row"]
    assert [b["y"] for b in lines] == sorted(b["y"] for b in lines)
    assert all(b["props"]["kind"] == "l2" and b["h"] == 48 for b in lines)
    undo(page)
    assert len(doc(page, client)["pages"]) == 1
    redo(page)
    assert len(doc(page, client)["pages"]) == 2


def test_a_long_blatt_runs_on_to_more_pages(editor):
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    store_words(page, client, [f"Wort{i}" for i in range(25)])
    list_tab(page)
    page.get_by_role("button", name="Lernwörter-Blatt").click()
    pages = doc(page, client)["pages"]
    # The page in use, then the Blatt over three pages of 9 rows a block (the last one has 7).
    assert len(pages) == 4
    assert [b["type"] for b in pages[1]["blocks"]][:2] == ["text", "name"]
    for mode in ["copy", "trace", "row"]:
        blocks = [b for p in pages[1:] for b in p["blocks"] if b["type"] == "ruling"]
        blocks = [b for b in blocks if b["props"]["list"] == mode]
        assert [b["props"].get("from", 0) for b in blocks] == [0, 9, 18]
    undo(page)
    assert len(doc(page, client)["pages"]) == 1


def test_a_long_blatt_on_an_empty_page_keeps_how_that_page_lies(editor):
    """Review of #571: the Blatt fills an empty landscape page; its run-on pages lie the same."""
    client = user()
    empty = {"blocks": [], "landscape": True, "grid": 5}
    words = [f"Wort{i}" for i in range(25)]
    page = editor(box("a", "text", TEXT), pages=[empty], client=client, words=words)
    page.locator('.sheet[data-page="1"]').click(position={"x": 40, "y": 40})
    expect(page.locator('.sheet[data-page="1"]')).to_have_class(re.compile(r"\bon\b"))
    list_tab(page)
    page.get_by_role("button", name="Lernwörter-Blatt").click()
    expect(page.locator(".sheet[data-page]")).not_to_have_count(2)
    pages = doc(page, client)["pages"]
    assert len(pages) > 2
    assert pages[1]["grid"] == 5
    for p in pages[1:]:
        assert p["landscape"] is True
        assert all(b["w"] == 297 - 2 * 15 for b in p["blocks"] if b["type"] == "ruling")


def test_a_short_blatt_is_one_page_as_before(editor):
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    store_words(page, client, ["Hund", "Katze", "Igel", "Reh", "Maus"])
    list_tab(page)
    page.get_by_role("button", name="Lernwörter-Blatt").click()
    stored = doc(page, client)
    assert len(stored["pages"]) == 2
    rulings_1 = [b for b in stored["pages"][1]["blocks"] if b["type"] == "ruling"]
    assert all("from" not in b["props"] for b in rulings_1)


def test_the_blatt_button_is_off_without_words(editor):
    page = editor(box("a", "text", TEXT), client=user())
    list_tab(page)
    expect(page.get_by_role("button", name="Lernwörter-Blatt")).to_be_disabled()


def test_the_blatt_takes_the_lineatur_that_holds_every_word(editor):
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    store_words(page, client, ["Hund", "Katze", "Maus", "Reh", "Igel", "Fuchs"])
    list_tab(page)
    page.get_by_role("button", name="Lernwörter-Blatt").click()
    lines = doc(page, client)["pages"][1]["blocks"][2:]
    # Six words need six rows: Lineatur 3 fits them in a third of the page, Lineatur 2 does not.
    assert all(b["props"]["kind"] == "l3" for b in lines)
