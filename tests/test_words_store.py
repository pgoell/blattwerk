"""An older build's save keeps the list, and the run-on Blatt prints its later pages."""
# The fixtures imported below are named again as a test's arguments.
# ruff: noqa: F811

import pytest
from playwright.sync_api import expect
from test_feed_print import sheet_id
from test_words import (
    LINKED,
    LONG,
    editor,  # noqa: F401
    field,
    list_tab,
    pdf_pages,
    ready,
    rulings,
    store_words,
)
from ui import (
    TEXT,
    at,
    box,
    copy_text,
    doc,
    sheet,
    user,
)


def test_a_paste_beside_a_word_joins_no_word_to_it(editor):
    """Review: pasted words keep to lines of their own, behind a word and before one."""
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    list_tab(page)
    field(page).click()
    page.keyboard.type("Igel")
    copy_text(page, "Hund, Katze")
    field(page).focus()
    page.keyboard.press("Control+End")
    page.keyboard.press("Control+v")
    expect(field(page)).to_have_value("Igel\nHund\nKatze")
    page.keyboard.press("Control+Home")
    page.keyboard.press("Control+v")
    expect(field(page)).to_have_value("Hund\nKatze\nIgel\nHund\nKatze")
    assert doc(page, client)["words"] == ["Hund", "Katze", "Igel", "Hund", "Katze"]


def test_a_save_from_a_build_that_knows_no_list_keeps_the_stored_list():
    """A window left open on the build before the Lernwörter sends a document that names no list:
    the server keeps the one it holds. A build that knows them names it, and an empty one is
    stored as no list."""
    client = user()
    blocks = [box("r", "ruling", LINKED)]
    made = sheet(client, blocks, words=["Hund", "Katze"])
    url = f"/api/sheets/{made['id']}"
    old = {k: v for k, v in made["doc"].items() if k != "words"}
    back = client.patch(url, json={"doc": old, "version": made["version"]}).json()
    assert back["doc"]["words"] == ["Hund", "Katze"]
    assert client.get(url).json()["doc"]["words"] == ["Hund", "Katze"]
    body = {"doc": {**old, "words": ["Reh"]}, "version": back["version"]}
    back = client.patch(url, json=body).json()
    assert back["doc"]["words"] == ["Reh"]
    body = {"doc": {**old, "words": []}, "version": back["version"]}
    back = client.patch(url, json=body).json()
    assert "words" not in back["doc"] and "words" not in client.get(url).json()["doc"]
    # With no list stored, a document that names none stores none.
    back = client.patch(url, json={"doc": old, "version": back["version"]}).json()
    assert "words" not in back["doc"]
    # Another account's sheet gives no list away, and takes none.
    other = user()
    assert other.patch(url, json={"doc": old, "version": 1}).status_code == 404


def test_a_change_kept_by_an_older_build_takes_the_sheets_list_and_deletes_none(editor):
    """Second review: a window on the build before the Lernwörter keeps its unsent change in the
    browser's store, without the list it did not know. The next build sends that change with the
    sheet's list, and reads it as no other version."""
    client = user()
    page = editor(box("r", "ruling", LINKED, h=40), client=client, words=["Hund", "Katze"])
    sheet_id = page.url.rsplit("/", 1)[1]
    got = client.get(f"/api/sheets/{sheet_id}").json()
    moved = {k: v for k, v in got["doc"].items() if k != "words"}
    moved["pages"] = [{"blocks": [{**got["doc"]["pages"][0]["blocks"][0], "x": 30}]}]
    record = {"owner": got["user_id"], "base": got["version"], "doc": moved, "name": got["title"]}
    page.evaluate(
        "([id, r]) => localStorage.setItem('unsaved:' + id, JSON.stringify(r))", [sheet_id, record]
    )
    page.reload()
    ready(page)
    expect(at(page, "r").locator(".listed .row")).to_have_count(2)
    expect(page.locator(".editor")).not_to_contain_text("auf einem anderen Gerät geändert")
    back = doc(page, client)
    assert back["words"] == ["Hund", "Katze"]
    assert rulings(back)[0]["x"] == 30


def test_the_run_on_blatt_prints_its_later_words_on_its_later_pages(editor, server):
    """#416 the PDF has a page per sheet page, and the Blatt's page 2 shows the 10th word on."""
    client = user()
    page = editor(client=client, words=LONG)
    list_tab(page)
    page.get_by_role("button", name="Lernwörter-Blatt").click()
    assert len(doc(page, client)["pages"]) == 3
    texts = pdf_pages(server, client, sheet_id(page))
    assert len(texts) == 3
    assert "Wort00" in texts[0] and "Wort09" not in texts[0]
    assert "Wort09" in texts[1] and "Wort00" not in texts[1]
    assert "Wort18" in texts[2] and "Wort17" not in texts[2]


def test_words_taken_out_leave_the_run_on_page_empty_with_no_warning(editor, server):
    """#416 a Blatt page past the list shows empty rows and the tab says nothing."""
    client = user()
    page = editor(client=client, words=LONG)
    list_tab(page)
    page.get_by_role("button", name="Lernwörter-Blatt").click()
    assert len(doc(page, client)["pages"]) == 3
    store_words(page, client, LONG[:12])
    expect(page.locator(".panel [role=status]")).to_have_count(0)
    texts = pdf_pages(server, client, sheet_id(page))
    assert "Wort09" in texts[1] and "Wort11" in texts[1]
    assert "Wort" not in texts[2]


def test_a_from_past_the_list_shows_empty_rows(editor, server):
    """#416 own: a ruling whose `from` is past the list has no word to show, and does not fail."""
    client = user()
    page = editor(box("a", "ruling", {**LINKED, "from": 30}, h=40), client=client)
    store_words(page, client, LONG[:5])
    expect(page.locator(".panel [role=status]")).to_have_count(0)
    texts = pdf_pages(server, client, sheet_id(page))
    assert "Wort" not in " ".join(texts)


def test_a_bad_from_counts_as_none(editor, server):
    """#416 own: a bad `from` shows the list from its first word."""
    client = user()
    page = editor(box("a", "ruling", {**LINKED, "from": -1}, h=40), client=client)
    store_words(page, client, LONG[:5])
    texts = pdf_pages(server, client, sheet_id(page))
    assert "Wort00" in " ".join(texts)


@pytest.mark.parametrize("typed", ["", "Haus\nMaus\nKuh\nEi\nZebra"])
def test_the_list_draws_no_spelling_lines(editor, typed):
    """#580: the browser checks no spelling in the list, empty or with words and the focus on it."""
    page = editor()
    list_tab(page)
    words = field(page)
    words.click()
    if typed:
        page.keyboard.type(typed)
    expect(words).to_have_attribute("spellcheck", "false")
    assert words.evaluate("e => e.spellcheck") is False
