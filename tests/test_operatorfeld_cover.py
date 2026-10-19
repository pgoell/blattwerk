"""An Operatorfeld grown over a block says so, and moves nothing; near the paper's foot it grows past the
margin and says so (#822, as the Pfeilbild #821)."""

import pytest
from playwright.sync_api import expect
from test_gaps import panel, step
from ui import TEXT, at, box, pick, saved, user

OF = {
    "centre": False,
    "count": 2,
    "columns": 2,
    "boxes": 4,
    "max": 20,
    "ops": ["+", "-"],
    "only": "none",
    "given": "start",
    "drawOps": True,
    "seed": 7,
}
FOOT = "Das Operatorfeld ragt unten über den Rand."
H = 85.99  # the default height: 75 * 180 / 157, rounded as insert.ts does


@pytest.fixture
def editor(editor):
    """The editor with its panel open, where the Operatorfeld's settings are."""

    def start(*blocks, **more):
        return editor(*blocks, theme="", **more)

    return start


def of(name="k", y=50, **more):
    """An Operatorfeld block of 180 by 85.99 mm over the blocks of z 1."""
    return box(name, "operatorfeld", OF, z=2, w=180, h=H, y=y, **more)


def hint(page):
    return page.locator('p[data-cover="operator"]')


def foot(page):
    return page.locator('p[data-foot="haus"], p[data-foot="over"]')


def more_fields(page):
    """Presses Ein Operatorfeld mehr once, and waits for the save."""
    step(page, lambda: panel(page, "Ein Operatorfeld mehr").click())


def test_an_operatorfeld_near_the_foot_grows_past_it_and_keeps_its_box_size(editor):
    """Layout: one more Operatorfeld (a second row) takes a block at y 110 past the margin's foot but not
    past the paper: the stored height grows, the box size stays, and the foot hint says so."""
    # y 110 puts the grown block between the margin's foot (282 mm) and the paper's edge (297 mm).
    client = user()
    page = editor(of(y=110), box("t", "text", TEXT, x=150, y=110, w=40, h=30), client=client)
    pick(page, "k")
    before = at(page, "k").locator("g.box rect").first.bounding_box()["width"]
    more_fields(page)
    stored = {b["id"]: b for b in saved(page, client)}
    assert stored["k"]["h"] > H and 282 < 110 + stored["k"]["h"] <= 297, stored["k"]
    assert stored["t"]["x"] == 150 and stored["t"]["y"] == 110, stored["t"]
    after = at(page, "k").locator("g.box rect").first.bounding_box()["width"]
    assert abs(after - before) <= 0.01 * before, (before, after)
    expect(foot(page).filter(has_text=FOOT)).to_be_visible()


def test_one_undo_takes_the_grown_height_and_the_foot_hint_back(editor):
    """Layout: one more Operatorfeld takes a block past the foot; one undo takes the grown height and the
    foot hint back, and the stored height is 85.99 again."""
    # y 110, as above.
    client = user()
    page = editor(of(y=110), box("t", "text", TEXT, x=150, y=110, w=40, h=30), client=client)
    pick(page, "k")
    expect(foot(page).filter(has_text=FOOT)).to_have_count(0)
    more_fields(page)
    expect(foot(page).filter(has_text=FOOT)).to_be_visible()
    assert {b["id"]: b for b in saved(page, client)}["k"]["h"] > H
    step(page, lambda: page.get_by_label("Rückgängig", exact=True).first.click())
    assert abs({b["id"]: b for b in saved(page, client)}["k"]["h"] - H) < 0.2
    expect(foot(page).filter(has_text=FOOT)).to_have_count(0)


def test_growing_over_a_text_warns_and_moves_nothing(editor):
    """Layout: one more Operatorfeld grows a block over a text: the text stays and the hint says the block
    covers it."""
    client = user()
    page = editor(of(y=20), box("t", "text", TEXT, y=110), client=client)
    pick(page, "k")
    expect(hint(page)).to_have_count(0)
    more_fields(page)
    stored = {b["id"]: b for b in saved(page, client)}
    assert stored["k"]["h"] > H, stored["k"]
    assert stored["t"]["y"] == 110, stored["t"]
    expect(hint(page)).to_be_visible()


def test_one_undo_takes_the_height_and_the_hint_back(editor):
    """Layout: one undo takes the grown height and the cover hint back, and the stored height is 85.99 again."""
    client = user()
    page = editor(of(y=20), box("t", "text", TEXT, y=110), client=client)
    pick(page, "k")
    more_fields(page)
    expect(hint(page)).to_be_visible()
    step(page, lambda: page.get_by_label("Rückgängig", exact=True).first.click())
    assert abs({b["id"]: b for b in saved(page, client)}["k"]["h"] - H) < 0.2
    expect(hint(page)).to_have_count(0)


def test_no_hint_while_nothing_overlaps(editor):
    """Layout: with no block under the Operatorfeld, growing it shows no cover hint."""
    client = user()
    page = editor(of(y=20), box("t", "text", TEXT, y=200), client=client)
    pick(page, "k")
    more_fields(page)
    expect(at(page, "k").locator(".operatorfeld")).to_be_visible()
    expect(hint(page)).to_have_count(0)
