"""A Zahlenmauer grown over a block says so, and moves nothing (#801)."""

import pytest
from playwright.sync_api import expect
from test_fix_blatt import pdf_pages
from test_gaps import panel, step
from ui import RECT, RULING, TABLE, TEXT, at, box, maths, pick, picture, saved, upload, user

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
TWELVE = {**MAUER, "count": 12}
FOOT = 297


@pytest.fixture
def editor(editor):
    """The editor with its panel open, where the Zahlenmauer's settings are."""

    def start(*blocks, **more):
        return editor(*blocks, theme="", **more)

    return start


def zw(name, props, h=60, **more):
    """A Zahlenmauer block of 180 mm wide, 60 mm high unless given, over the blocks of z 1."""
    return box(name, "zahlenmauer", props, z=2, w=180, h=h, **more)


def test_a1_twelve_walls_over_a_text_move_nothing_and_warn(editor):
    """A1: grown to 12 walls over a text, the text stays and the panel says the walls cover it."""
    client = user()
    page = editor(zw("z", MAUER, y=15), box("t", "text", TEXT, y=80), client=client)
    pick(page, "z")
    for _ in range(8):
        step(page, lambda: panel(page, "Eine Mauer mehr").click())
    expect(page.locator('.block[data-id="z"] g.wall')).to_have_count(12)
    stored = {b["id"]: b for b in saved(page, client)}
    assert stored["t"]["y"] == 80, stored["t"]
    expect(page.locator('[data-cover="wall"]')).to_be_visible()


def test_a2_the_pdf_has_one_page_and_draws_the_text(editor, server):
    """A2: the grown sheet prints on one page, and the text is on it."""
    client = user()
    page = editor(zw("z", MAUER, y=15), box("t", "text", TEXT, y=80), client=client)
    pick(page, "z")
    for _ in range(8):
        step(page, lambda: panel(page, "Eine Mauer mehr").click())
    pages = pdf_pages(server, client, page.url.rsplit("/", 1)[1])
    assert len(pages) == 1, pages
    assert "Hallo" in pages[0], pages


def test_a3_near_the_foot_the_wall_ends_at_the_foot_and_prints_one_page(editor, server):
    """A3: a Zahlenmauer low on the page grows to the foot and no further; the PDF has one page."""
    client = user()
    page = editor(zw("z", MAUER, y=220), client=client)
    pick(page, "z")
    for _ in range(8):
        step(page, lambda: panel(page, "Eine Mauer mehr").click())
    stored = {b["id"]: b for b in saved(page, client)}["z"]
    assert stored["y"] + stored["h"] <= FOOT + 0.01, stored
    pages = pdf_pages(server, client, page.url.rsplit("/", 1)[1])
    assert len(pages) == 1, pages


def test_a4_one_undo_takes_wall_height_and_hint_back_and_redo_brings_them(editor):
    """A4: one click to 5 walls grows the block over a text; one undo takes both back, redo brings both."""
    client = user()
    page = editor(zw("z", MAUER, y=15), box("t", "text", TEXT, y=76), client=client)
    pick(page, "z")
    expect(page.locator('[data-cover="wall"]')).to_have_count(0)
    step(page, lambda: panel(page, "Eine Mauer mehr").click())
    grown = {b["id"]: b for b in saved(page, client)}["z"]["h"]
    expect(page.locator('[data-cover="wall"]')).to_be_visible()
    step(page, lambda: page.get_by_label("Rückgängig", exact=True).first.click())
    assert {b["id"]: b for b in saved(page, client)}["z"]["h"] == 60
    expect(page.locator('[data-cover="wall"]')).to_have_count(0)
    step(page, lambda: page.get_by_label("Wiederholen", exact=True).first.click())
    assert {b["id"]: b for b in saved(page, client)}["z"]["h"] == grown
    expect(page.locator('[data-cover="wall"]')).to_be_visible()


def test_i1_moving_the_text_away_takes_the_hint(editor):
    """I1: with the wall hint showing, moving the text down to Y 270 takes the hint away."""
    page = editor(zw("z", TWELVE, y=15, h=208), box("t", "text", TEXT, z=3, y=80))
    pick(page, "z")
    expect(page.locator('[data-cover="wall"]')).to_be_visible()
    pick(page, "t")
    page.locator(".geo").get_by_label("Y", exact=True).fill("270")
    page.locator(".geo").get_by_label("Y", exact=True).press("Enter")
    pick(page, "z")
    expect(page.locator('[data-cover="wall"]')).to_have_count(0)


UNDER = {
    "text": lambda c: box("t", "text", TEXT, y=100),
    "shape with text": lambda c: box("t", "shape", {**RECT, "text": "Hallo"}, y=100),
    "image": lambda c: {**picture(upload(c)), "id": "t", "y": 100},
    "table": lambda c: box("t", "table", TABLE, y=100),
    "ruling": lambda c: box("t", "ruling", RULING, y=100),
    "maths": lambda c: box("t", "maths", maths(c), y=100),
    "zahlenmauer": lambda c: box("t", "zahlenmauer", MAUER, w=180, h=60, y=100),
    "text in a group of its own": lambda c: {**box("t", "text", TEXT, y=100), "group": ["g"]},
}


@pytest.mark.parametrize("kind", list(UNDER))
def test_i2_every_kind_of_block_under_the_walls_counts(editor, kind):
    """I2: each kind of block under a 12-wall Zahlenmauer gets the wall hint."""
    client = user()
    page = editor(zw("z", TWELVE, y=15, h=208), UNDER[kind](client), client=client)
    pick(page, "z")
    expect(page.locator('[data-cover="wall"]')).to_be_visible()


def test_i2_a_bare_shape_does_not_count(editor):
    """I2: a shape without text under the walls gets no wall hint."""
    page = editor(zw("z", TWELVE, y=15, h=208), box("t", "shape", RECT, y=100))
    pick(page, "z")
    expect(page.locator('[data-cover="wall"]')).to_have_count(0)


def test_i2_a_block_of_its_own_group_does_not_count(editor):
    """I2: a text in the Zahlenmauer's own group under the walls gets no wall hint."""
    page = editor(
        {**zw("z", TWELVE, y=15, h=208), "group": ["g"]},
        {**box("t", "text", TEXT, y=100), "group": ["g"]},
    )
    at(page, "z").click()
    expect(page.locator('[data-cover="wall"]')).to_have_count(0)


def test_i3_no_hint_while_the_walls_stay_clear(editor):
    """I3: four walls with the text at Y 200 do not reach it, so no wall hint."""
    page = editor(zw("z", MAUER, y=15), box("t", "text", TEXT, y=200))
    pick(page, "z")
    expect(page.locator('[data-cover="wall"]')).to_have_count(0)
