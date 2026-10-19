"""A Rechentabelle grown over a block says so, and moves nothing; near the paper's foot it grows past the
margin and says so (#824, as the Rechenrad #823)."""

import pytest
from playwright.sync_api import expect
from test_gaps import panel, step
from ui import TEXT, at, box, pick, saved, user

RT = {
    "count": 2,
    "columns": 2,
    "rows": 4,
    "cols": 4,
    "op": "+",
    "max": 20,
    "seed": 7,
}
FOOT = "Die Rechentabelle ragt unten über den Rand."
COVER = "Die Rechentabelle liegt über einem anderen Block. Verschiebe ihn oder mache die Rechentabelle kleiner."
H = 84.22  # the default height: 51 * 180 / 109, rounded as insert.ts does


@pytest.fixture
def editor(editor):
    """The editor with its panel open, where the Rechentabelle's settings are."""

    def start(*blocks, **more):
        return editor(*blocks, theme="", **more)

    return start


def rt(name="k", y=50, **more):
    """A Rechentabelle block of 180 by 84.22 mm over the blocks of z 1."""
    return box(name, "rechentabelle", RT, z=2, w=180, h=H, y=y, **more)


def hint(page):
    return page.locator('p[data-cover="rechentabelle"]')


def foot(page):
    return page.locator('p[data-foot="haus"], p[data-foot="over"]')


def more_row(page):
    """Presses Eine Zeile mehr once, and waits for the save."""
    step(page, lambda: panel(page, "Eine Zeile mehr").click())


def test_a_rechentabelle_near_the_foot_grows_past_it_and_keeps_its_cell_size(editor):
    """Layout: one more row takes a block at y 190 past the margin's foot but not past the paper: the
    stored height grows, the cell size stays, and the foot hint says so."""
    # y 190 puts the grown block between the margin's foot (282 mm) and the paper's edge (297 mm).
    client = user()
    page = editor(rt(y=190), box("t", "text", TEXT, x=150, y=190, w=40, h=30), client=client)
    pick(page, "k")
    before = at(page, "k").locator("g.cell").first.bounding_box()["width"]
    more_row(page)
    stored = {b["id"]: b for b in saved(page, client)}
    assert stored["k"]["h"] > H and 282 < 190 + stored["k"]["h"] <= 297, stored["k"]
    assert stored["t"]["x"] == 150 and stored["t"]["y"] == 190, stored["t"]
    after = at(page, "k").locator("g.cell").first.bounding_box()["width"]
    assert abs(after - before) <= 0.01 * before, (before, after)
    expect(foot(page).filter(has_text=FOOT)).to_be_visible()


def test_one_undo_takes_the_grown_height_and_the_foot_hint_back(editor):
    """Layout: one more row takes a block past the foot; one undo takes the grown height and the foot
    hint back, and the stored height is 84.22 again."""
    # y 190, as above.
    client = user()
    page = editor(rt(y=190), box("t", "text", TEXT, x=150, y=190, w=40, h=30), client=client)
    pick(page, "k")
    expect(foot(page).filter(has_text=FOOT)).to_have_count(0)
    more_row(page)
    expect(foot(page).filter(has_text=FOOT)).to_be_visible()
    assert {b["id"]: b for b in saved(page, client)}["k"]["h"] > H
    step(page, lambda: page.get_by_label("Rückgängig", exact=True).first.click())
    assert abs({b["id"]: b for b in saved(page, client)}["k"]["h"] - H) < 0.2
    expect(foot(page).filter(has_text=FOOT)).to_have_count(0)


def test_growing_over_a_text_warns_and_moves_nothing(editor):
    """Layout: one more row grows a block over a text: the text stays and the hint says the block
    covers it."""
    client = user()
    page = editor(rt(y=20), box("t", "text", TEXT, y=110), client=client)
    pick(page, "k")
    expect(hint(page)).to_have_count(0)
    more_row(page)
    stored = {b["id"]: b for b in saved(page, client)}
    assert stored["k"]["h"] > H, stored["k"]
    assert stored["t"]["y"] == 110, stored["t"]
    expect(hint(page)).to_be_visible()
    expect(hint(page)).to_have_text(COVER)


def test_one_undo_takes_the_height_and_the_hint_back(editor):
    """Layout: one undo takes the grown height and the cover hint back, and the stored height is 84.22
    again."""
    client = user()
    page = editor(rt(y=20), box("t", "text", TEXT, y=110), client=client)
    pick(page, "k")
    more_row(page)
    expect(hint(page)).to_be_visible()
    step(page, lambda: page.get_by_label("Rückgängig", exact=True).first.click())
    assert abs({b["id"]: b for b in saved(page, client)}["k"]["h"] - H) < 0.2
    expect(hint(page)).to_have_count(0)


def test_no_hint_while_nothing_overlaps(editor):
    """Layout: with no block under the Rechentabelle, growing it shows no cover hint."""
    client = user()
    page = editor(rt(y=20), box("t", "text", TEXT, y=200), client=client)
    pick(page, "k")
    more_row(page)
    expect(at(page, "k").locator(".rechentabelle")).to_be_visible()
    expect(hint(page)).to_have_count(0)
