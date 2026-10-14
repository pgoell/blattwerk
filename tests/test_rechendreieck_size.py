"""A Rechendreieck grows taller with more triangles, so that its triangles keep their size (#578).

A field a pupil writes into never draws smaller than in the default block (4 in a row, 180 mm
wide). More rows make the block taller; fewer rows never shrink it. The sizes are measured on the
screen: the first triangle's polygon, and the block's own box, before and after each change.
"""

import pytest
from playwright.sync_api import expect
from test_gaps import panel, step
from ui import box, pick, saved, user

DREIECK = {"count": 4, "columns": 4, "max": 20, "given": "inner", "empty": False, "seed": 7}


@pytest.fixture
def editor(editor):
    """The editor with its panel open, where the Rechendreieck's settings are."""

    def start(*blocks, **more):
        return editor(*blocks, theme="", **more)

    return start


def dz(name, props):
    """A Rechendreieck block of 180 by 50 mm."""
    return box(name, "rechendreieck", props, w=180, h=50)


def triangle_height(page):
    """The height of the first triangle's outline on the screen, in px."""
    outline = page.locator('.block[data-id="d"] g.triangle[data-triangle="0"] polygon')
    return outline.bounding_box()["height"]


def block_height(page):
    """The height of the block's box on the screen, in px."""
    return page.locator('.block[data-id="d"]').bounding_box()["height"]


def stored_h(client, page):
    """The block's stored height in mm."""
    return {b["id"]: b for b in saved(page, client)}["d"]["h"]


def test_twelve_triangles_keep_the_size_of_four_and_the_block_grows(editor):
    """#578: "Ein Dreieck mehr" 8 times gives 12 triangles at the size of the 4; the block grows."""
    client = user()
    page = editor(dz("d", DREIECK), client=client)
    pick(page, "d")
    before, block_before = triangle_height(page), block_height(page)
    for _ in range(8):
        step(page, lambda: panel(page, "Ein Dreieck mehr").click())
    expect(page.locator('.block[data-id="d"] g.triangle')).to_have_count(12)
    assert triangle_height(page) == pytest.approx(before, rel=0.02)
    assert block_height(page) > block_before * 1.5
    assert stored_h(client, page) > 50


def test_two_columns_for_four_triangles_keep_their_size(editor):
    """Own case: "Eine Spalte weniger" makes 4 triangles two rows high, and they keep their size."""
    client = user()
    page = editor(dz("d", DREIECK), client=client)
    pick(page, "d")
    before = triangle_height(page)
    step(page, lambda: panel(page, "Eine Spalte weniger").click())
    expect(page.locator('.block[data-id="d"] g.triangle')).to_have_count(4)
    assert triangle_height(page) >= before * 0.98
    assert stored_h(client, page) > 50


def test_back_from_twelve_to_four_the_block_does_not_shrink(editor):
    """Own case: 12 triangles, then 8 times "Ein Dreieck weniger": the block keeps its height."""
    client = user()
    page = editor(dz("d", DREIECK), client=client)
    pick(page, "d")
    before = triangle_height(page)
    for _ in range(8):
        step(page, lambda: panel(page, "Ein Dreieck mehr").click())
    grown = stored_h(client, page)
    for _ in range(8):
        step(page, lambda: panel(page, "Ein Dreieck weniger").click())
    expect(page.locator('.block[data-id="d"] g.triangle')).to_have_count(4)
    assert stored_h(client, page) >= grown
    assert triangle_height(page) == pytest.approx(before, rel=0.02)


def test_one_undo_takes_back_the_triangle_and_the_height(editor):
    """#578: a fifth triangle opens a second row and grows the block; one undo takes back both,
    one redo brings both again."""
    client = user()
    page = editor(dz("d", DREIECK), client=client)
    pick(page, "d")
    step(page, lambda: panel(page, "Ein Dreieck mehr").click())
    grown = stored_h(client, page)
    assert grown > 50
    step(page, lambda: page.get_by_label("Rückgängig", exact=True).first.click())
    assert stored_h(client, page) == 50
    step(page, lambda: page.get_by_label("Wiederholen", exact=True).first.click())
    assert stored_h(client, page) == grown


def test_the_block_grows_no_further_than_the_page_foot(editor):
    """#578: a block low on the page grows to the page's foot and no further; the triangles then
    draw as large as that room allows."""
    client = user()
    page = editor(box("d", "rechendreieck", DREIECK, w=180, h=50, y=220), client=client)
    pick(page, "d")
    for _ in range(8):
        step(page, lambda: panel(page, "Ein Dreieck mehr").click())
    block = {b["id"]: b for b in saved(page, client)}["d"]
    sheet = page.locator(".sheet").first.bounding_box()
    drawn = page.locator('.block[data-id="d"]').bounding_box()
    assert block["h"] > 50
    assert drawn["y"] + drawn["height"] <= sheet["y"] + sheet["height"] + 1


@pytest.mark.parametrize("act", ["zahlenraum", "leer"])
def test_another_setting_leaves_a_short_block_as_it_is(editor, act):
    """#578 review: only Dreiecke and Spalten grow the block. A saved 12-triangle block at 50 mm
    keeps its height when the Zahlenraum or Leer changes."""
    client = user()
    page = editor(dz("d", {**DREIECK, "count": 12}), client=client)
    pick(page, "d")
    controls = page.locator(".panel")
    if act == "zahlenraum":
        step(page, lambda: controls.get_by_label("Zahlenraum").select_option("100"))
    else:
        step(page, lambda: controls.get_by_role("button", name="Leer", exact=True).click())
    assert stored_h(client, page) == 50
