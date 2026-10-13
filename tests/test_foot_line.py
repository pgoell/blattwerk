"""The panel says at its top when a picked block hangs over the page's foot (issue #496).

The line is the first thing in the right panel, whatever the block is. A block that hangs over
says that what is under the edge is not printed. Each test names the case it proves.
"""

import pytest
from playwright.sync_api import expect
from test_suchsel import SUCHSEL
from ui import LINE, RECT, RULING, TABLE, TEXT, at, box, maths, pick, picture, upload, user

ONE = "Der Block ragt unten über die Seite hinaus. Was unter dem Rand steht, wird nicht gedruckt."
LINE_OVER = '[data-foot="over"]'


def hangs(page):
    """The line stands above the fields, "Position und Größe" first, and shows without scrolling."""
    line = page.locator(f".panel {LINE_OVER}")
    expect(line).to_be_visible()
    above = "() => document.querySelector('.panel [data-foot=\"over\"]').nextElementSibling"
    assert page.evaluate(f"{above}.classList.contains('geo')"), "the line is not above the fields"
    box_ = line.bounding_box()
    assert box_["y"] >= 0 and box_["y"] + box_["height"] <= page.viewport_size["height"], box_
    assert page.locator(".panel").evaluate("el => el.scrollTop") == 0


def blocks_of(client):
    """One block of each type, its lower edge below the A4 foot of 297 mm."""
    return {
        "text": [box("a", "text", TEXT, y=290, h=20)],
        "shape": [box("a", "shape", RECT, y=290, h=20)],
        "line": [box("a", "shape", LINE, y=290, h=20)],
        "picture": [box("a", "image", picture(upload(client))["props"], y=290, h=20)],
        "table": [box("a", "table", TABLE, y=290, h=20)],
        "lineatur": [box("a", "ruling", RULING, y=290, h=20)],
        "maths": [box("a", "maths", maths(client), y=290, h=20)],
        "suchsel": [box("a", "suchsel", SUCHSEL, y=290, h=20)],
        "points": [box("a", "points", {"max": 10}, y=290, h=20)],
        "group": [
            box("a", "shape", RECT, y=20, h=20, group=["g"]),
            box("b", "shape", RECT, z=2, y=290, h=20, group=["g"]),
        ],
    }


@pytest.mark.parametrize(
    "kind",
    [
        "text",
        "shape",
        "line",
        "picture",
        "table",
        "lineatur",
        "maths",
        "suchsel",
        "points",
        "group",
    ],
)
def test_a14_the_line_leads_the_panel_for_every_block_type(editor, kind):
    """A14"""
    client = user()
    page = editor(*blocks_of(client)[kind], client=client)
    at(page, "a").click()
    hangs(page)
    if kind == "group":
        expect(page.locator(".block.sel")).to_have_count(2)


def test_a14_a_maths_block_states_the_foot_once(editor):
    """A14: the maths block's own line under Anzahl is the one line, moved up."""
    client = user()
    page = editor(*blocks_of(client)["maths"], client=client)
    pick(page, "a")
    hangs(page)
    expect(page.locator(LINE_OVER)).to_have_count(1)


def test_a14_several_picked_one_hanging_says_the_selection_hangs(editor):
    """A14: two blocks picked, one of them over the foot: the line speaks of the selection."""
    client = user()
    page = editor(
        box("a", "text", TEXT, y=20, h=20),
        box("b", "shape", RECT, z=2, y=290, h=20),
        client=client,
    )
    pick(page, "a", "b")
    hangs(page)
    expect(page.locator(LINE_OVER)).to_contain_text("Die Auswahl ragt unten über die Seite hinaus.")


def test_a14_a_block_wholly_on_the_page_shows_no_line(editor):
    """A14 guard: a block that ends on the page has no line."""
    client = user()
    page = editor(box("a", "text", TEXT, y=20, h=20), client=client)
    pick(page, "a")
    expect(page.locator(LINE_OVER)).to_have_count(0)


def test_a15_the_line_goes_when_the_block_is_typed_back_on_the_page(editor):
    """A15: typing Y back up takes the line away."""
    client = user()
    page = editor(box("a", "text", TEXT, y=290, h=20), client=client)
    pick(page, "a")
    expect(page.locator(LINE_OVER)).to_be_visible()
    page.get_by_label("Y", exact=True).fill("60")
    page.get_by_label("Y", exact=True).press("Enter")
    expect(page.locator(LINE_OVER)).to_have_count(0)


def test_i6_a_turned_block_counts_by_its_lowest_corner(editor):
    """I6: the box ends on the page, but its lowest corner is 6 mm below the foot."""
    client = user()
    page = editor(box("a", "shape", RECT, y=265, w=60, h=20, angle=45), client=client)
    pick(page, "a")
    hangs(page)


def test_i6_on_a_landscape_page_the_foot_is_210(editor):
    """I6: on a page on its side the foot is 210 mm, so a block at 200 to 220 mm hangs over."""
    client = user()
    page = editor(
        client=client, pages=[{"blocks": [box("a", "text", TEXT, y=200, h=20)], "landscape": True}]
    )
    pick(page, "a")
    hangs(page)


def test_i7_undo_of_the_move_takes_the_line_away(editor):
    """I7: undo of the move that pushed the block over the foot takes the line away."""
    client = user()
    page = editor(box("a", "text", TEXT, y=20, h=20), client=client)
    pick(page, "a")
    page.get_by_label("Y", exact=True).fill("290")
    page.get_by_label("Y", exact=True).press("Enter")
    hangs(page)
    at(page, "a").click()
    page.keyboard.press("Control+z")
    expect(page.locator(LINE_OVER)).to_have_count(0)
