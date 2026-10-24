"""Undo walks the list, the link and the cut, and a copied linked block takes the list with it."""
# The fixtures imported below are named again as a test's arguments.
# ruff: noqa: F811

import pytest
from playwright.sync_api import expect
from test_words import (
    LINKED,
    editor,  # noqa: F401
    field,
    go,
    list_tab,
    ready,
    redo,
    rulings,
    state,
    store_words,
    undo,
)
from ui import (
    RULING,
    TEXT,
    at,
    box,
    doc,
    pick,
    sheet,
    thumb,
    unpick,
    user,
)


def test_undo_and_redo_walk_the_list_the_link_the_mode_and_the_cut(editor):
    client = user()
    page = editor(box("r", "ruling", RULING), client=client)
    list_tab(page)
    field(page).click()
    page.keyboard.type("Hund")
    expect(field(page)).to_have_value("Hund")
    pick(page, "r")
    page.get_by_role("tab", name="Format").click()
    select = page.get_by_label("Text der Lineatur")
    select.select_option("copy")
    select.select_option("row")
    select.select_option("own")
    expect(select).to_have_value("own")
    steps = [
        (None, None, None, None),
        (["Hund"], None, None, None),
        (["Hund"], "copy", None, None),
        (["Hund"], "row", None, None),
        (["Hund"], None, "Hund", True),
    ]
    assert state(doc(page, client)) == steps[4]
    for want in [steps[3], steps[2], steps[1], steps[0]]:
        undo(page)
        assert state(doc(page, client)) == want
    for want in steps[1:]:
        redo(page)
        assert state(doc(page, client)) == want


def test_a_run_of_typing_in_the_list_is_one_undo_step(editor):
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    list_tab(page)
    field(page).click()
    page.keyboard.type("Hund")
    page.keyboard.press("Enter")
    page.keyboard.type("Katze")
    expect(field(page)).to_have_value("Hund\nKatze")
    undo(page)
    assert "words" not in doc(page, client)
    expect(field(page)).to_have_value("")


def test_ctrl_z_in_the_list_undoes_the_sheet(editor):
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    list_tab(page)
    field(page).click()
    page.keyboard.type("Hund")
    expect(field(page)).to_have_value("Hund")
    page.keyboard.press("Control+z")
    expect(field(page)).to_have_value("")
    assert "words" not in doc(page, client)


def test_several_lineaturen_link_in_one_step(editor):
    client = user()
    page = editor(
        box("a", "ruling", {**RULING, "list": "trace"}),
        box("b", "ruling", RULING, z=2),
        client=client,
    )
    store_words(page, client, ["Hund", "Katze"])
    pick(page, "a", "b")
    select = page.get_by_label("Text der Lineatur")
    expect(select).to_have_value("own")
    select.select_option("copy")
    assert [r["props"]["list"] for r in rulings(doc(page, client))] == ["copy", "copy"]
    undo(page)
    assert [r["props"].get("list") for r in rulings(doc(page, client))] == ["trace", None]
    select.select_option("row")
    unpick(page)
    pick(page, "a", "b")
    expect(page.get_by_label("Text der Lineatur")).to_have_value("row")


@pytest.mark.parametrize("how", ["dblclick", "enter", "typing"])
def test_a_linked_block_opens_no_field(editor, how):
    client = user()
    page = editor(box("r", "ruling", {**LINKED, "text": "eigen"}), client=client)
    store_words(page, client, ["Hund", "Katze"])
    if how == "dblclick":
        at(page, "r").dblclick()
    else:
        pick(page, "r")
        if how == "enter":
            page.keyboard.press("Enter")
        else:
            page.keyboard.type("x")
    expect(page.locator("textarea.written:not([readonly])")).to_have_count(0)
    stored = doc(page, client)
    assert rulings(stored)[0]["props"]["text"] == "eigen"
    assert stored["words"] == ["Hund", "Katze"]


def test_a_sheet_without_a_list_saves_back_as_it_was(editor):
    client = user()
    page = editor(box("r", "ruling", RULING), client=client)
    pick(page, "r")
    page.keyboard.press("ArrowRight")
    stored = doc(page, client)
    assert rulings(stored)[0]["x"] == 16
    assert "words" not in stored
    assert "list" not in rulings(stored)[0]["props"]


def test_emptying_the_list_removes_it(editor):
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    store_words(page, client, ["Hund"])
    list_tab(page)
    field(page).fill("")
    assert "words" not in doc(page, client)


@pytest.mark.parametrize("junk", ["Hund", 7])
def test_garbage_in_words_shows_an_empty_list(editor, junk):
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    store_words(page, client, junk)
    list_tab(page)
    expect(field(page)).to_have_value("")
    expect(page.get_by_role("button", name="Lernwörter-Blatt")).to_be_disabled()
    field(page).click()
    page.keyboard.type("Reh")
    assert doc(page, client)["words"] == ["Reh"]


def test_a_reload_a_duplicate_and_a_template_keep_the_list(editor):
    client = user()
    page = editor(box("r", "ruling", LINKED), client=client)
    store_words(page, client, ["Hund", "Katze"])
    page.reload()
    ready(page)
    stored = doc(page, client)
    assert stored["words"] == ["Hund", "Katze"]
    assert rulings(stored)[0]["props"]["list"] == "copy"

    sheet_id = page.url.rsplit("/", 1)[1]
    copied = client.post(f"/api/sheets/{sheet_id}/duplicate").json()["doc"]
    assert copied["words"] == ["Hund", "Katze"]
    assert rulings(copied)[0]["props"]["list"] == "copy"

    page.get_by_label("Name der Vorlage").fill("Lernwörter-Vorlage")
    page.get_by_role("button", name="Dieses Blatt als Vorlage").click()
    # The template is there once the server has answered: a page that leaves before then never
    # sent it, and the other sheet has no such template to pick (#448).
    template = page.get_by_role("button", name="Lernwörter-Vorlage", exact=True)
    expect(template).to_be_visible()
    other = sheet(client, [])
    go(page, other)
    template.click()
    stored = doc(page, client)
    assert stored["words"] == ["Hund", "Katze"]
    assert rulings(stored)[0]["props"]["list"] == "copy"


def test_a_copied_linked_block_takes_the_list_to_a_sheet_without_one(editor):
    client = user()
    page = editor(box("r", "ruling", LINKED), client=client)
    store_words(page, client, ["Hund", "Katze"])
    other = sheet(client, [box("t", "text", TEXT, z=3)])
    pick(page, "r")
    page.keyboard.press("Control+c")
    go(page, other)
    page.keyboard.press("Control+v")
    expect(page.locator(".sheet .block")).to_have_count(2)
    stored = doc(page, client)
    assert stored["words"] == ["Hund", "Katze"]
    assert rulings(stored)[0]["props"]["list"] == "copy"
    undo(page)
    stored = doc(page, client)
    assert "words" not in stored
    assert rulings(stored) == []


def test_a_copied_linked_block_lands_cut_loose_on_a_sheet_with_another_list(editor):
    client = user()
    page = editor(box("r", "ruling", LINKED), client=client)
    store_words(page, client, ["Hund", "Katze"])
    other = sheet(client, [box("t", "text", TEXT, z=3)])
    pick(page, "r")
    page.keyboard.press("Control+c")
    go(page, other)
    store_words(page, client, ["Reh"])
    page.keyboard.press("Control+v")
    expect(page.locator(".sheet .block")).to_have_count(2)
    stored = doc(page, client)
    assert stored["words"] == ["Reh"]
    props = rulings(stored)[0]["props"]
    # Another list than the sheet's: the words go in as the block's own text.
    assert "list" not in props
    assert props["text"] == "Hund\nKatze"


def test_a_duplicated_block_and_a_copied_page_stay_linked(editor):
    client = user()
    page = editor(box("r", "ruling", LINKED), client=client)
    store_words(page, client, ["Hund", "Katze"])
    pick(page, "r")
    page.keyboard.press("Control+d")
    expect(page.locator(".sheet .block")).to_have_count(2)
    thumb(page, 0).focus()
    page.keyboard.press("Control+d")
    stored = doc(page, client)
    assert stored["words"] == ["Hund", "Katze"]
    assert len(stored["pages"]) == 2
    assert [r["props"].get("list") for r in rulings(stored)] == ["copy", "copy"]
    assert [r["props"].get("list") for r in rulings(stored, 1)] == ["copy", "copy"]
