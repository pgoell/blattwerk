"""A Rechenrad grown over a block says so, and moves nothing; near the paper's foot it grows past the
margin and says so (#823, as the Operatorfeld #822)."""

import pytest
from playwright.sync_api import expect
from test_gaps import panel, step
from ui import TEXT, at, box, pick, saved, user

RR = {
    "count": 2,
    "columns": 2,
    "rings": 2,
    "segments": 8,
    "max": 20,
    "op": "+",
    "task": "outer",
    "seed": 7,
}
FOOT = "Das Rechenrad ragt unten über den Rand."
COVER = (
    "Das Rechenrad liegt über einem anderen Block. Verschiebe ihn oder mache das Rechenrad kleiner."
)
H = 85.53  # the default height: 67 * 180 / 141, rounded as insert.ts does


@pytest.fixture
def editor(editor):
    """The editor with its panel open, where the Rechenrad's settings are."""

    def start(*blocks, **more):
        return editor(*blocks, theme="", **more)

    return start


def rr(name="k", y=50, **more):
    """A Rechenrad block of 180 by 85.53 mm over the blocks of z 1."""
    return box(name, "rechenrad", RR, z=2, w=180, h=H, y=y, **more)


def hint(page):
    return page.locator('p[data-cover="rechenrad"]')


def foot(page):
    return page.locator('p[data-foot="haus"], p[data-foot="over"]')


def more_wheels(page):
    """Presses Ein Rechenrad mehr once, and waits for the save."""
    step(page, lambda: panel(page, "Ein Rechenrad mehr").click())


def test_a_rechenrad_near_the_foot_grows_past_it_and_keeps_its_wheel_size(editor):
    """Layout: one more Rechenrad (a second row) takes a block at y 110 past the margin's foot but not past
    the paper: the stored height grows, the wheel size stays, and the foot hint says so."""
    # y 110 puts the grown block between the margin's foot (282 mm) and the paper's edge (297 mm).
    client = user()
    page = editor(rr(y=110), box("t", "text", TEXT, x=150, y=110, w=40, h=30), client=client)
    pick(page, "k")
    before = at(page, "k").locator("g.wheel").first.bounding_box()["width"]
    more_wheels(page)
    stored = {b["id"]: b for b in saved(page, client)}
    assert stored["k"]["h"] > H and 282 < 110 + stored["k"]["h"] <= 297, stored["k"]
    assert stored["t"]["x"] == 150 and stored["t"]["y"] == 110, stored["t"]
    after = at(page, "k").locator("g.wheel").first.bounding_box()["width"]
    assert abs(after - before) <= 0.01 * before, (before, after)
    expect(foot(page).filter(has_text=FOOT)).to_be_visible()


def test_one_undo_takes_the_grown_height_and_the_foot_hint_back(editor):
    """Layout: one more Rechenrad takes a block past the foot; one undo takes the grown height and the foot
    hint back, and the stored height is 85.53 again."""
    # y 110, as above.
    client = user()
    page = editor(rr(y=110), box("t", "text", TEXT, x=150, y=110, w=40, h=30), client=client)
    pick(page, "k")
    expect(foot(page).filter(has_text=FOOT)).to_have_count(0)
    more_wheels(page)
    expect(foot(page).filter(has_text=FOOT)).to_be_visible()
    assert {b["id"]: b for b in saved(page, client)}["k"]["h"] > H
    step(page, lambda: page.get_by_label("Rückgängig", exact=True).first.click())
    assert abs({b["id"]: b for b in saved(page, client)}["k"]["h"] - H) < 0.2
    expect(foot(page).filter(has_text=FOOT)).to_have_count(0)


def test_growing_over_a_text_warns_and_moves_nothing(editor):
    """Layout: one more Rechenrad grows a block over a text: the text stays and the hint says the block
    covers it."""
    client = user()
    page = editor(rr(y=20), box("t", "text", TEXT, y=110), client=client)
    pick(page, "k")
    expect(hint(page)).to_have_count(0)
    more_wheels(page)
    stored = {b["id"]: b for b in saved(page, client)}
    assert stored["k"]["h"] > H, stored["k"]
    assert stored["t"]["y"] == 110, stored["t"]
    expect(hint(page)).to_be_visible()
    expect(hint(page)).to_have_text(COVER)


def test_one_undo_takes_the_height_and_the_hint_back(editor):
    """Layout: one undo takes the grown height and the cover hint back, and the stored height is 85.53 again."""
    client = user()
    page = editor(rr(y=20), box("t", "text", TEXT, y=110), client=client)
    pick(page, "k")
    more_wheels(page)
    expect(hint(page)).to_be_visible()
    step(page, lambda: page.get_by_label("Rückgängig", exact=True).first.click())
    assert abs({b["id"]: b for b in saved(page, client)}["k"]["h"] - H) < 0.2
    expect(hint(page)).to_have_count(0)


def test_no_hint_while_nothing_overlaps(editor):
    """Layout: with no block under the Rechenrad, growing it shows no cover hint."""
    client = user()
    page = editor(rr(y=20), box("t", "text", TEXT, y=200), client=client)
    pick(page, "k")
    more_wheels(page)
    expect(at(page, "k").locator(".rechenrad")).to_be_visible()
    expect(hint(page)).to_have_count(0)
