"""A Zahlenkette grown over a block says so, and moves nothing; near the paper's foot it grows past the
margin and says so (#820, as the Zahlenhaus #819)."""

import pytest
from playwright.sync_api import expect
from test_gaps import panel, step
from ui import TEXT, at, box, pick, saved, user

KETTE = {
    "count": 4,
    "columns": 2,
    "rings": 6,
    "max": 20,
    "op": "+",
    "showStep": False,
    "given": "start",
    "seed": 7,
}


@pytest.fixture
def editor(editor):
    """The editor with its panel open, where the Zahlenkette's settings are."""

    def start(*blocks, **more):
        return editor(*blocks, theme="", **more)

    return start


def kette(name="k", y=50, count=4, **more):
    """A Zahlenkette block of 180 by 39 mm over the blocks of z 1, with `count` chains."""
    return box(name, "zahlenkette", {**KETTE, "count": count}, z=2, w=180, h=39, y=y, **more)


def hint(page):
    return page.locator('p[data-cover="kette"]')


def foot(page):
    return page.locator('p[data-foot="haus"], p[data-foot="over"]')


def more_chains(page):
    """Presses Eine Kette mehr once, and waits for the save."""
    step(page, lambda: panel(page, "Eine Kette mehr").click())


def test_a_chain_near_the_foot_grows_past_it_and_keeps_its_ring_size(editor):
    """Four more Ketten (count 8, four rows) grow a chain at y 205 past the margin's foot: it takes the
    height it needs, its digits keep their size, and the foot hint says so."""
    client = user()
    page = editor(kette(y=205), box("t", "text", TEXT, x=150, y=205, w=40, h=30), client=client)
    pick(page, "k")
    before = at(page, "k").locator("svg text").first.bounding_box()["height"]
    for _ in range(4):
        more_chains(page)
    stored = {b["id"]: b for b in saved(page, client)}
    assert stored["k"]["h"] > 39 and 282 < 205 + stored["k"]["h"] <= 297, stored["k"]
    assert stored["t"]["x"] == 150 and stored["t"]["y"] == 205, stored["t"]
    after = at(page, "k").locator("svg text").first.bounding_box()["height"]
    assert abs(after - before) <= 0.01 * before, (before, after)
    expect(foot(page)).to_be_visible()


def test_one_undo_takes_the_grown_height_and_the_foot_hint_back(editor):
    """One more Kette (count 6, three rows) takes a chain at y 230 past the foot; one undo takes the
    grown height and the foot hint back, and the stored height is 39 again."""
    client = user()
    page = editor(kette(y=230), box("t", "text", TEXT, x=150, y=230, w=40, h=30), client=client)
    pick(page, "k")
    expect(foot(page)).to_have_count(0)
    more_chains(page)
    expect(foot(page)).to_be_visible()
    assert {b["id"]: b for b in saved(page, client)}["k"]["h"] > 39
    step(page, lambda: page.get_by_label("Rückgängig", exact=True).first.click())
    assert {b["id"]: b for b in saved(page, client)}["k"]["h"] == 39
    expect(foot(page)).to_have_count(0)


def test_raising_the_chains_grows_the_chain_over_a_text_and_moves_nothing(editor):
    """Six Ketten grow a chain over a text: the text stays and the hint says the chain covers it."""
    client = user()
    page = editor(kette(y=20), box("t", "text", TEXT, y=70), client=client)
    pick(page, "k")
    expect(hint(page)).to_have_count(0)
    more_chains(page)
    more_chains(page)
    stored = {b["id"]: b for b in saved(page, client)}
    assert stored["k"]["h"] > 39, stored["k"]
    assert stored["t"]["y"] == 70, stored["t"]
    expect(hint(page)).to_be_visible()


def test_one_undo_takes_the_height_and_the_hint_back(editor):
    """One undo takes the grown height and the hint back, and the stored height is 39 again."""
    client = user()
    page = editor(kette(y=20), box("t", "text", TEXT, y=70), client=client)
    pick(page, "k")
    more_chains(page)
    more_chains(page)
    expect(hint(page)).to_be_visible()
    step(page, lambda: page.get_by_label("Rückgängig", exact=True).first.click())
    step(page, lambda: page.get_by_label("Rückgängig", exact=True).first.click())
    assert {b["id"]: b for b in saved(page, client)}["k"]["h"] == 39
    expect(hint(page)).to_have_count(0)


def test_no_hint_while_nothing_overlaps(editor):
    """With no text under the chain, growing it shows no hint."""
    client = user()
    page = editor(kette(y=50), box("t", "text", TEXT, y=200), client=client)
    pick(page, "k")
    more_chains(page)
    more_chains(page)
    expect(at(page, "k").locator(".zahlenkette")).to_be_visible()
    expect(hint(page)).to_have_count(0)
