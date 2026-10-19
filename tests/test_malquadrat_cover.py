"""A Malquadrat grown over a block says so, and moves nothing; near the paper's foot it grows past the
margin and says so (#826, as the Magisches Quadrat #825).

The hint texts are copied from the Malquadrat's own panel and drawing: check them against the panel when the block draws.
"""

import pytest
from playwright.sync_api import expect
from test_gaps import panel, step
from ui import TEXT, at, box, pick, saved, user

MQ = {
    "count": 2,
    "columns": 2,
    "size": 3,
    "op": "*",
    "reihen": [2, 3, 4, 5, 6, 7, 8, 9],
    "max": 20,
    "task": "factors",
    "seed": 7,
}
FOOT = "Das Malquadrat ragt unten über den Rand."
COVER = "Das Malquadrat liegt über einem anderen Block. Verschiebe ihn oder mache das Malquadrat kleiner."
H = 93.98  # the default height: 59 * 180 / 113, rounded as insert.ts does


@pytest.fixture
def editor(editor):
    """The editor with its panel open, where the Malquadrat's settings are."""

    def start(*blocks, **more):
        return editor(*blocks, theme="", **more)

    return start


def mq(name="k", y=5, **more):
    """A Malquadrat block of 180 by 93.98 mm over the blocks of z 1."""
    return box(name, "malquadrat", MQ, z=2, w=180, h=H, y=y, **more)


def hint(page):
    return page.locator('p[data-cover="malquadrat"]')


def foot(page):
    return page.locator('p[data-foot="haus"], p[data-foot="over"]')


def more_square(page):
    """Presses Ein Malquadrat mehr once, and waits for the save: 3 squares make 2 lines, so the block grows."""
    step(page, lambda: panel(page, "Ein Malquadrat mehr").click())


def test_a_malquadrat_near_the_foot_grows_past_it_and_keeps_its_cell_size(editor):
    """Layout (#826): one more square takes a block at y 95 past the margin's foot but not past the paper: the
    stored height grows, the cell size stays, and the foot hint says so."""
    # y 95 puts the grown block (121 * 180 / 113 = 192.74 mm high) between the margin's foot (282 mm) and the paper's
    # edge (297 mm).
    client = user()
    page = editor(mq(y=95), box("t", "text", TEXT, x=150, y=80, w=40, h=30), client=client)
    pick(page, "k")
    before = at(page, "k").locator("g.cell").first.bounding_box()["width"]
    more_square(page)
    stored = {b["id"]: b for b in saved(page, client)}
    assert stored["k"]["h"] > H and 282 < 95 + stored["k"]["h"] <= 297, stored["k"]
    assert stored["t"]["x"] == 150 and stored["t"]["y"] == 80, stored["t"]
    after = at(page, "k").locator("g.cell").first.bounding_box()["width"]
    assert abs(after - before) <= 0.01 * before, (before, after)
    expect(foot(page).filter(has_text=FOOT)).to_be_visible()


def test_one_undo_takes_the_grown_height_and_the_foot_hint_back(editor):
    """Layout (#826): one more square takes a block past the foot; one undo takes the grown height and the foot
    hint back, and the stored height is 93.98 again."""
    # y 95, as above.
    client = user()
    page = editor(mq(y=95), box("t", "text", TEXT, x=150, y=80, w=40, h=30), client=client)
    pick(page, "k")
    expect(foot(page).filter(has_text=FOOT)).to_have_count(0)
    more_square(page)
    expect(foot(page).filter(has_text=FOOT)).to_be_visible()
    assert {b["id"]: b for b in saved(page, client)}["k"]["h"] > H
    step(page, lambda: page.get_by_label("Rückgängig", exact=True).first.click())
    assert abs({b["id"]: b for b in saved(page, client)}["k"]["h"] - H) < 0.2
    expect(foot(page).filter(has_text=FOOT)).to_have_count(0)


def test_growing_over_a_text_warns_and_moves_nothing(editor):
    """Layout (#826): one more square grows a block over a text: the text stays and the hint says the block
    covers it."""
    client = user()
    page = editor(mq(y=5), box("t", "text", TEXT, y=110), client=client)
    pick(page, "k")
    expect(hint(page)).to_have_count(0)
    more_square(page)
    stored = {b["id"]: b for b in saved(page, client)}
    assert stored["k"]["h"] > H, stored["k"]
    assert stored["t"]["y"] == 110, stored["t"]
    expect(hint(page)).to_be_visible()
    expect(hint(page)).to_have_text(COVER)


def test_one_undo_takes_the_height_and_the_hint_back(editor):
    """Layout (#826): one undo takes the grown height and the cover hint back, and the stored height is 93.98
    again."""
    client = user()
    page = editor(mq(y=5), box("t", "text", TEXT, y=110), client=client)
    pick(page, "k")
    more_square(page)
    expect(hint(page)).to_be_visible()
    step(page, lambda: page.get_by_label("Rückgängig", exact=True).first.click())
    assert abs({b["id"]: b for b in saved(page, client)}["k"]["h"] - H) < 0.2
    expect(hint(page)).to_have_count(0)


def test_no_hint_while_nothing_overlaps(editor):
    """Layout (#826): with no block under the Malquadrat, growing it shows no cover hint."""
    client = user()
    page = editor(mq(y=5), box("t", "text", TEXT, y=240), client=client)
    pick(page, "k")
    more_square(page)
    expect(at(page, "k").locator(".malquadrat")).to_be_visible()
    expect(hint(page)).to_have_count(0)
