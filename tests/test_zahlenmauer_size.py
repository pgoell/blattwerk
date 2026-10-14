"""A Zahlenmauer grows taller with more walls, so that its stones keep their size (#588).

A field a pupil writes into never draws smaller than in the default block (4 walls in 2
columns, 180 by 60 mm). More walls make the block taller; fewer walls never shrink it. The sizes
are measured on the screen: the first stone's rectangle, and the block's own box, before and
after each change.
"""

import pytest
from playwright.sync_api import expect
from test_gaps import panel, step
from ui import box, pick, saved, user

MAUER = {
    "base": 3,
    "count": 4,
    "columns": 2,
    "max": 20,
    "op": "+",
    "given": "base",
    "empty": False,
    "seed": 7,
}


@pytest.fixture
def editor(editor):
    """The editor with its panel open, where the Zahlenmauer's settings are."""

    def start(*blocks, **more):
        return editor(*blocks, theme="", **more)

    return start


def zw(name, props, **more):
    """A Zahlenmauer block of 180 by 60 mm."""
    return box(name, "zahlenmauer", props, w=180, h=60, **more)


def stone_height(page):
    """The height of the first wall's first stone on the screen, in px."""
    stone = page.locator('.block[data-id="d"] g.wall[data-wall="0"] rect').first
    return stone.bounding_box()["height"]


def block_height(page):
    """The height of the block's box on the screen, in px."""
    return page.locator('.block[data-id="d"]').bounding_box()["height"]


def stored_h(client, page):
    """The block's stored height in mm."""
    return {b["id"]: b for b in saved(page, client)}["d"]["h"]


def test_twelve_walls_keep_the_size_of_four_and_the_block_grows(editor):
    """#588: "Eine Mauer mehr" 8 times gives 12 walls at the size of the 4; the block grows."""
    client = user()
    page = editor(zw("d", MAUER), client=client)
    pick(page, "d")
    before, block_before = stone_height(page), block_height(page)
    for _ in range(8):
        step(page, lambda: panel(page, "Eine Mauer mehr").click())
    expect(page.locator('.block[data-id="d"] g.wall')).to_have_count(12)
    assert stone_height(page) == pytest.approx(before, rel=0.02)
    assert block_height(page) > block_before * 1.5
    assert stored_h(client, page) > 60


def test_back_from_twelve_to_four_the_block_does_not_shrink(editor):
    """#588: 12 walls, then 8 times "Eine Mauer weniger": the block keeps its height."""
    client = user()
    page = editor(zw("d", MAUER), client=client)
    pick(page, "d")
    before = stone_height(page)
    for _ in range(8):
        step(page, lambda: panel(page, "Eine Mauer mehr").click())
    grown = stored_h(client, page)
    for _ in range(8):
        step(page, lambda: panel(page, "Eine Mauer weniger").click())
    expect(page.locator('.block[data-id="d"] g.wall')).to_have_count(4)
    assert stored_h(client, page) >= grown
    assert stone_height(page) >= before * 0.98


def test_one_undo_takes_back_the_wall_and_the_height(editor):
    """#588: a fifth wall opens a second row and grows the block; one undo takes back both,
    one redo brings both again."""
    client = user()
    page = editor(zw("d", MAUER), client=client)
    pick(page, "d")
    step(page, lambda: panel(page, "Eine Mauer mehr").click())
    grown = stored_h(client, page)
    assert grown > 60
    step(page, lambda: page.get_by_label("Rückgängig", exact=True).first.click())
    assert stored_h(client, page) == 60
    step(page, lambda: page.get_by_label("Wiederholen", exact=True).first.click())
    assert stored_h(client, page) == grown


def test_the_block_grows_no_further_than_the_page_foot(editor):
    """#588: a block low on the page grows to the page's foot and no further."""
    client = user()
    page = editor(zw("d", MAUER, y=220), client=client)
    pick(page, "d")
    for _ in range(8):
        step(page, lambda: panel(page, "Eine Mauer mehr").click())
    block = {b["id"]: b for b in saved(page, client)}["d"]
    sheet = page.locator(".sheet").first.bounding_box()
    drawn = page.locator('.block[data-id="d"]').bounding_box()
    assert block["h"] > 60
    assert drawn["y"] + drawn["height"] <= sheet["y"] + sheet["height"] + 1


def test_a_saved_twelve_wall_block_keeps_its_height_when_the_zahlenraum_changes(editor):
    """#588: a block saved with 12 walls at 60 mm stays at 60 mm when the Zahlenraum changes."""
    client = user()
    page = editor(zw("d", {**MAUER, "count": 12}), client=client)
    pick(page, "d")
    step(page, lambda: page.locator(".panel").get_by_label("Zahlenraum").select_option("100"))
    assert stored_h(client, page) == 60


def test_base_five_keeps_the_size_of_base_three(editor):
    """Own case: "Grundsteine" 3 to 5 makes walls wider; the block grows, stones keep size."""
    client = user()
    page = editor(zw("d", MAUER), client=client)
    pick(page, "d")
    before = stone_height(page)
    step(page, lambda: page.locator(".panel").get_by_label("Grundsteine").select_option("5"))
    expect(page.locator('.block[data-id="d"] g.wall[data-wall="0"] g.stone')).to_have_count(15)
    assert stone_height(page) == pytest.approx(before, rel=0.02)
    assert stored_h(client, page) > 60


def test_fewer_columns_keep_the_size_of_the_stones(editor):
    """Own case: "Eine Spalte weniger" stacks 4 walls in one column; stones keep size."""
    client = user()
    page = editor(zw("d", MAUER), client=client)
    pick(page, "d")
    before = stone_height(page)
    step(page, lambda: panel(page, "Eine Spalte weniger").click())
    expect(page.locator('.block[data-id="d"] g.wall')).to_have_count(4)
    assert stone_height(page) >= before * 0.98
    assert stored_h(client, page) > 60
