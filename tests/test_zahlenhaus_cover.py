"""A Zahlenhaus grown over a block says so, and moves nothing (#819)."""

import pytest
from playwright.sync_api import expect
from test_gaps import step
from ui import TEXT, at, box, pick, saved, user

HAUS = {"count": 4, "columns": 4, "floors": 4, "max": 10, "given": "side", "seed": 7}


@pytest.fixture
def editor(editor):
    """The editor with its panel open, where the Zahlenhaus's settings are."""

    def start(*blocks, **more):
        return editor(*blocks, theme="", **more)

    return start


def haus(name="h", y=15, **more):
    """A Zahlenhaus block of 120 by 55 mm over the blocks of z 1."""
    return box(name, "zahlenhaus", HAUS, z=2, w=120, h=55, y=y, **more)


def hint(page):
    return page.locator('p[data-cover="haus"]')


def floors(page, n):
    """Sets Stockwerke in the panel, and waits for the save."""
    select = page.locator(".panel").get_by_label("Stockwerke", exact=True)
    step(page, lambda: select.select_option(str(n)))


def test_a_house_near_the_foot_grows_past_it_and_keeps_its_digit_size(editor):
    """Stockwerke 8 grows a house past the page's foot: it takes the height it needs, its digits keep their size, and the hint says it hangs over the edge."""
    client = user()
    page = editor(haus(y=240), box("t", "text", TEXT, x=150, y=240, w=40, h=30), client=client)
    pick(page, "h")
    before = at(page, "h").locator("svg text").first.bounding_box()["height"]
    floors(page, 8)
    stored = {b["id"]: b for b in saved(page, client)}
    assert stored["h"]["h"] > 55 and 240 + stored["h"]["h"] > 282, stored["h"]
    assert stored["t"]["x"] == 150 and stored["t"]["y"] == 240, stored["t"]
    after = at(page, "h").locator("svg text").first.bounding_box()["height"]
    assert abs(after - before) <= 0.01 * before, (before, after)
    expect(page.locator('p[data-foot="haus"], p[data-foot="over"]')).to_be_visible()


def test_one_undo_takes_the_grown_height_and_the_foot_hint_back(editor):
    """One undo takes the grown height and the foot hint back, and the stored height is 55 again."""
    client = user()
    page = editor(haus(y=200), box("t", "text", TEXT, x=150, y=200, w=40, h=30), client=client)
    pick(page, "h")
    expect(page.locator('p[data-foot="haus"], p[data-foot="over"]')).to_have_count(0)
    floors(page, 10)
    foot = page.locator('p[data-foot="haus"], p[data-foot="over"]')
    expect(foot).to_be_visible()
    step(page, lambda: page.get_by_label("Rückgängig", exact=True).first.click())
    assert {b["id"]: b for b in saved(page, client)}["h"]["h"] == 55
    expect(foot).to_have_count(0)


def test_raising_the_floors_grows_the_house_over_a_text_and_moves_nothing(editor):
    """Stockwerke 10 grows the house over a text: the text stays and the hint says the house covers it."""
    client = user()
    page = editor(haus(), box("t", "text", TEXT, y=80), client=client)
    pick(page, "h")
    expect(hint(page)).to_have_count(0)
    floors(page, 10)
    stored = {b["id"]: b for b in saved(page, client)}
    assert stored["h"]["h"] > 55, stored["h"]
    assert stored["t"]["y"] == 80, stored["t"]
    expect(hint(page)).to_contain_text("Das Zahlenhaus liegt über einem anderen Block.")


def test_one_undo_takes_the_height_and_the_hint_back(editor):
    """One undo takes the grown height and the hint back, and the stored height is 55 again."""
    client = user()
    page = editor(haus(), box("t", "text", TEXT, y=80), client=client)
    pick(page, "h")
    floors(page, 10)
    expect(hint(page)).to_be_visible()
    step(page, lambda: page.get_by_label("Rückgängig", exact=True).first.click())
    assert {b["id"]: b for b in saved(page, client)}["h"]["h"] == 55
    expect(hint(page)).to_have_count(0)


def test_no_hint_while_nothing_overlaps(editor):
    """With no text under the house, growing it shows no hint."""
    client = user()
    page = editor(haus(), box("t", "text", TEXT, y=200), client=client)
    pick(page, "h")
    floors(page, 10)
    expect(at(page, "h").locator(".zahlenhaus")).to_be_visible()
    expect(hint(page)).to_have_count(0)
