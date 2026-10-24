"""The format painter does not grow a maths block past the foot."""

from playwright.sync_api import expect
from test_maths_foot import (
    FOOT,
    height,
    on_sheet,
    tasks,
)
from test_painter import paint
from ui import (
    box,
    maths,
    pick,
    user,
)


def test_i4_the_painter_does_not_grow_a_maths_block_past_the_foot(editor):
    """I4: the painter lays 20 pt on a block at the foot: it keeps 14 pt and stays on the sheet."""
    client = user()
    big = maths(client, ops=["+", "-"], max=100, count=12, columns=3, size=20, format="row")
    small = maths(client, ops=["+", "-"], max=100, count=12, columns=3, size=14, format="row")
    page = editor(
        box("a", "maths", big, y=20, h=height(big)),
        box("m", "maths", small, y=FOOT - height(small) - 1, h=height(small)),
        client=client,
    )
    paint(page, "a", "m")
    pick(page, "m")
    expect(tasks(page).nth(2)).to_have_text("14 pt")
    on_sheet(page, "m")


def test_i4_the_painter_does_not_grow_a_block_sized_by_hand(editor):
    """I4 by hand: the painter's 10 pt would move the foot below the page: the block keeps 14 pt."""
    client = user()
    small = maths(client, ops=["+", "-"], max=100, count=12, columns=3, size=10, format="row")
    mine = maths(client, ops=["+", "-"], max=100, count=12, columns=3, size=14, format="row")
    page = editor(
        box("a", "maths", small, y=20, h=height(small)),
        box("m", "maths", mine, y=270, h=20),
        client=client,
    )
    paint(page, "a", "m")
    pick(page, "m")
    expect(tasks(page).nth(2)).to_have_text("14 pt")
    on_sheet(page, "m")
