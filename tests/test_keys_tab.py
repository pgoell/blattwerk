"""Tab walks the blocks, a group, a crop and an open field.

Shared pieces live in test_keys.py."""

from playwright.sync_api import expect
from ui import (
    FIELD,
    ITEM,
    RECT,
    TEXT,
    at,
    box,
    expect_picked,
    pick,
    picked,
    picture,
    stopped,
    unpick,
    upload,
    user,
)


def test_tab_goes_through_the_blocks_from_back_to_front(editor):
    # The order on the sheet is not the order in the document.
    page = editor(box("c", "text", TEXT, z=3), box("a", "text", TEXT), box("b", "shape", RECT, z=2))
    pick(page, "a")
    for name in ("b", "c", "a"):
        page.keyboard.press("Tab")
        expect_picked(page, name)
    for name in ("c", "b", "a"):
        page.keyboard.press("Shift+Tab")
        expect_picked(page, name)


def test_tab_stops_once_at_a_group(editor):
    group = {"group": ["g"]}
    page = editor(
        box("a", "text", TEXT),
        box("b", "text", TEXT, z=2, **group),
        box("c", "text", TEXT, z=3, **group),
        box("d", "text", TEXT, z=4),
    )
    pick(page, "a")
    for names in (["b", "c"], ["d"], ["a"]):
        page.keyboard.press("Tab")
        expect_picked(page, *names)
    for names in (["d"], ["b", "c"], ["a"]):
        page.keyboard.press("Shift+Tab")
        expect_picked(page, *names)


def test_tab_with_nothing_selected_starts_at_the_back_or_the_front(editor):
    page = editor(box("c", "text", TEXT, z=3), box("a", "text", TEXT), box("b", "shape", RECT, z=2))
    page.keyboard.press("Tab")
    expect_picked(page, "a")
    unpick(page)
    page.keyboard.press("Shift+Tab")
    expect_picked(page, "c")
    # A button that has the focus keeps the key.
    unpick(page)
    page.get_by_label("Größer", exact=True).focus()
    page.keyboard.press("Shift+Tab")
    expect(page.get_by_label("Größer", exact=True)).not_to_be_focused()
    assert page.evaluate("document.activeElement.tagName") == "BUTTON"
    assert picked(page) == []


def test_tab_on_an_empty_page_stays_the_browsers(editor):
    page = editor()
    assert not stopped(page, "Tab")
    assert page.evaluate("document.activeElement !== document.body")


def test_tab_starts_at_a_group_as_a_whole(editor):
    group = {"group": ["g"]}
    page = editor(
        box("a", "text", TEXT, **group),
        box("b", "text", TEXT, z=2, **group),
        box("c", "text", TEXT, z=3),
    )
    page.keyboard.press("Tab")
    expect_picked(page, "a", "b")
    # Enter and F2 open nothing in a group.
    for key in ("Enter", "F2"):
        page.keyboard.press(key)
        assert page.locator(".ProseMirror").count() == 0
        assert picked(page) == ["a", "b"]


def test_tab_goes_on_from_the_front_most_of_several_and_stays_on_its_page(editor):
    names = ("a", "b", "c", "d")
    page = editor(
        *(box(name, "text", TEXT, z=z) for z, name in enumerate(names, 1)),
        more=[box("far", "text", TEXT)],
    )
    pick(page, "a", "c")
    page.keyboard.press("Tab")
    expect_picked(page, "d")
    # Past the front it starts over at the back of the same page.
    page.keyboard.press("Tab")
    expect_picked(page, "a")
    page.keyboard.press("Shift+Tab")
    expect_picked(page, "d")
    # The other page has its own round, of one block that stays selected.
    at(page, "far").click()
    expect_picked(page, "far")
    for key in ("Tab", "Shift+Tab"):
        assert stopped(page, key)
        assert picked(page) == ["far"]


def test_tab_ends_a_crop_and_goes_on(editor):
    client = user()
    page = editor(
        box("a", "text", TEXT), {**picture(upload(client)), "id": "bild", "z": 2}, client=client
    )
    at(page, "bild").dblclick()
    expect(page.locator(".crop")).to_have_count(1)
    page.keyboard.press("Tab")
    expect(page.locator(".crop")).to_have_count(0)
    expect_picked(page, "a")


def test_tab_in_a_field_moves_an_item_in(editor):
    page = editor(box("a", "text", ITEM), box("b", "text", TEXT, z=2))
    pick(page, "a")
    page.keyboard.press("Enter")
    page.keyboard.press("Tab")
    expect(page.locator(f"{FIELD} p")).to_have_attribute("data-level", "1")
    expect(page.locator(FIELD)).to_be_focused()
    assert picked(page) == ["a"]
