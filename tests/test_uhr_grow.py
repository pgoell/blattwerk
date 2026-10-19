"""An Uhr grows downward when its clocks grow in number, so that the clocks keep their size (#598).

The default block (4 clocks in 4 columns, 180 by 58.5 mm) draws its clocks at the scale of its
width. More clocks make the block taller, fewer never shrink it, and a block low on the page stops
at the page's foot. The sizes are measured on the screen: a clock's face, before and after each
change, and the block's stored height.
"""

import pytest
from playwright.sync_api import expect
from test_gaps import step
from ui import TEXT, at, box, pick, saved, user

UHR = {
    "numbers": "all",
    "minutes": True,
    "ring": False,
    "task": "read",
    "answer": "box",
    "format": "12",
    "region": "nach",
    "count": 4,
    "cols": 4,
    "step": 15,
    "fill": "random",
    "times": [60, 135, 210, 285],
    "seed": 7,
}


def uhr(name, props, h=58.5, y=20, **more):
    """An Uhr block of 180 mm wide and h mm high, y mm from the top: at 20 mm it has room for 234
    mm above the bottom margin."""
    return box(name, "uhr", props, w=180, h=h, y=y, **more)


def field(page, label):
    return page.locator(".panel").get_by_label(label, exact=True)


def stored(page, client):
    """The Uhr's block as the server holds it."""
    return {b["id"]: b for b in saved(page, client)}["d"]


def face(page):
    """The width in px of the first clock's face on the screen."""
    return at(page, "d").locator("circle.face").first.bounding_box()["width"]


def test_twelve_clocks_in_three_columns_grow_the_block_and_keep_the_clock_size(editor):
    """#598: 12 clocks in 3 columns make the block 234 mm high, and its clocks are not smaller."""
    client = user()
    page = editor(uhr("d", UHR), client=client)
    pick(page, "d")
    before = face(page)
    step(page, lambda: field(page, "Uhren").fill("12"))
    step(page, lambda: field(page, "Spalten").fill("3"))
    assert stored(page, client)["h"] == 234
    assert face(page) >= before * 0.98


def test_back_to_four_clocks_the_block_does_not_shrink(editor):
    """#598: 12 clocks in 3 columns, then 4 clocks: the block keeps its 234 mm."""
    client = user()
    page = editor(uhr("d", UHR), client=client)
    pick(page, "d")
    step(page, lambda: field(page, "Uhren").fill("12"))
    step(page, lambda: field(page, "Spalten").fill("3"))
    step(page, lambda: field(page, "Uhren").fill("4"))
    expect(at(page, "d").locator("circle.face")).to_have_count(4)
    assert stored(page, client)["h"] == 234


def test_one_undo_takes_back_the_clocks_and_the_height(editor):
    """#598: 12 clocks grow the block to 175.5 mm; one undo gives back 4 clocks and 58.5 mm."""
    client = user()
    page = editor(uhr("d", UHR), client=client)
    pick(page, "d")
    step(page, lambda: field(page, "Uhren").fill("12"))
    assert stored(page, client)["h"] == 175.5
    step(page, lambda: page.get_by_label("Rückgängig", exact=True).first.click())
    assert stored(page, client)["h"] == 58.5
    assert stored(page, client)["props"]["count"] == 4


def foot(page):
    """The hint that says a block hangs over the page's foot."""
    return page.locator('p[data-foot="haus"], p[data-foot="over"]')


def test_911_a_block_low_on_the_page_grows_past_the_foot_and_keeps_its_clock_size(editor):
    """#911: a block at 115 mm from the top grows past the foot at 282 mm and ends above the paper's edge; its clocks keep their size,
    the text beside it does not move, and the hint says it hangs over the edge."""
    client = user()
    page = editor(
        uhr("d", UHR, y=115), box("t", "text", TEXT, x=150, y=115, w=40, h=30), client=client
    )
    pick(page, "d")
    before = face(page)
    step(page, lambda: field(page, "Uhren").fill("12"))
    block = stored(page, client)
    assert block["y"] + block["h"] > 282, block
    assert face(page) == pytest.approx(before, rel=0.01)
    assert {b["id"]: b for b in saved(page, client)}["t"]["y"] == 115
    expect(foot(page)).to_be_visible()


def test_911_one_undo_takes_the_grown_height_and_the_foot_hint_back(editor):
    """#911: 12 clocks at 115 mm grow the block past the foot; one undo takes the height and the hint back."""
    client = user()
    page = editor(uhr("d", UHR, y=115), client=client)
    pick(page, "d")
    expect(foot(page)).to_have_count(0)
    step(page, lambda: field(page, "Uhren").fill("12"))
    expect(foot(page)).to_be_visible()
    step(page, lambda: page.get_by_label("Rückgängig", exact=True).first.click())
    assert stored(page, client)["h"] == 58.5
    expect(foot(page)).to_have_count(0)


def test_six_columns_are_width_bound_and_the_block_takes_their_height(editor):
    """#598, beyond the brief: 12 clocks in 6 columns are 600 by 260 units, so 180 mm wide makes the
    block 78 mm high."""
    client = user()
    page = editor(uhr("d", UHR), client=client)
    pick(page, "d")
    step(page, lambda: field(page, "Spalten").fill("6"))
    step(page, lambda: field(page, "Uhren").fill("12"))
    assert stored(page, client)["h"] == 78


def test_a_stored_block_keeps_its_height_when_a_setting_changes(editor):
    """#598, beyond the brief: a block saved 234 mm high keeps it when the minute ticks go off."""
    client = user()
    page = editor(uhr("d", {**UHR, "count": 12, "cols": 3}, h=234), client=client)
    pick(page, "d")
    step(page, lambda: field(page, "Minutenstriche").uncheck())
    assert stored(page, client)["h"] == 234
