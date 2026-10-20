"""A Zehnerfeld block grown over a block says so, and moves nothing; near the paper's foot it grows past the
margin and says so (#829, as the Halbschriftlich #828).

The hint words are those of frontend/src/pages/Format.tsx.
"""

import pytest
from playwright.sync_api import expect
from test_gaps import panel, step
from ui import TEXT, at, box, pick, saved, user

ZEH = {
    "count": 6,
    "columns": 2,
    "field": "zwanzig",
    "op": "+",
    "task": "dots",
    "max": 20,
    "cross": "any",
    "lines": True,
    "colors": "color",
    "manual": False,
    "seed": 7,
}
FOOT = "Das Zehnerfeld ragt unten über den Rand."
COVER = (
    "Das Zehnerfeld liegt über einem anderen Block. Verschiebe ihn oder mache das Zehnerfeld "
    "kleiner."
)
H = 82  # the default height of 6 tasks: 3 rows of 23 mm, 2 gaps of 6 mm and 1 mm of stroke, at 127 mm wide
GROWN = 111  # 4 rows of tasks: 4 · 23 + 3 · 6 + 1


@pytest.fixture
def editor(editor):
    """The editor with its panel open, where the Zehnerfeld settings are."""

    def start(*blocks, **more):
        return editor(*blocks, theme="", **more)

    return start


def zeh(y=5, **more):
    """A Zehnerfeld block of 127 by 82 mm over the blocks of z 1."""
    return box("k", "zehnerfeld", ZEH, z=2, w=127, h=H, y=y, **more)


def hint(page):
    return page.locator('p[data-cover="zehnerfeld"]')


def foot(page):
    return page.locator('p[data-foot="haus"], p[data-foot="over"]')


def more_row(page):
    """Presses Eine Aufgabe mehr once and waits for the save: the seventh task makes a fourth row, so the block grows."""
    step(page, lambda: panel(page, "Eine Aufgabe mehr").click())


def undo_row(page):
    step(page, lambda: page.get_by_label("Rückgängig", exact=True).first.click())


def test_a_zehnerfeld_near_the_foot_grows_past_it_and_keeps_its_task_size(editor):
    """Layout (#829): one more row takes a block at y 180 past the margin's foot but not past the paper: the stored
    height grows, the task size stays, and the foot hint says so."""
    # y 180 puts the grown block (111 mm high) between the margin's foot (282 mm) and the paper's edge (297 mm).
    client = user()
    page = editor(zeh(y=180), box("t", "text", TEXT, x=150, y=60, w=40, h=20), client=client)
    pick(page, "k")
    before = at(page, "k").locator("g.task").first.bounding_box()["width"]
    more_row(page)
    stored = {b["id"]: b for b in saved(page, client)}
    assert stored["k"]["h"] == GROWN and 282 < 180 + stored["k"]["h"] <= 297, stored["k"]
    after = at(page, "k").locator("g.task").first.bounding_box()["width"]
    assert abs(after - before) <= 0.01 * before, (before, after)
    expect(foot(page).filter(has_text=FOOT)).to_be_visible()


def test_one_undo_takes_the_grown_height_and_the_foot_hint_back(editor):
    """Layout (#829): one more row takes a block past the foot; one undo takes the grown height and the foot hint
    back, and the stored height is 82 again."""
    client = user()
    page = editor(zeh(y=180), client=client)
    pick(page, "k")
    expect(foot(page).filter(has_text=FOOT)).to_have_count(0)
    more_row(page)
    expect(foot(page).filter(has_text=FOOT)).to_be_visible()
    assert {b["id"]: b for b in saved(page, client)}["k"]["h"] == GROWN
    undo_row(page)
    assert abs({b["id"]: b for b in saved(page, client)}["k"]["h"] - H) < 0.2
    expect(foot(page).filter(has_text=FOOT)).to_have_count(0)


def test_growing_over_a_text_warns_and_moves_nothing(editor):
    """Layout (#829): one more row grows a block over a text: the text stays and the hint says the block covers it."""
    client = user()
    page = editor(zeh(y=5), box("t", "text", TEXT, y=100), client=client)
    pick(page, "k")
    expect(hint(page)).to_have_count(0)
    more_row(page)
    stored = {b["id"]: b for b in saved(page, client)}
    assert stored["k"]["h"] == GROWN, stored["k"]
    assert stored["t"]["y"] == 100, stored["t"]
    expect(hint(page)).to_be_visible()
    expect(hint(page)).to_have_text(COVER)


def test_one_undo_takes_the_height_and_the_hint_back(editor):
    """Layout (#829): one undo takes the grown height and the cover hint back, and the stored height is 82 again."""
    client = user()
    page = editor(zeh(y=5), box("t", "text", TEXT, y=100), client=client)
    pick(page, "k")
    more_row(page)
    expect(hint(page)).to_be_visible()
    undo_row(page)
    assert abs({b["id"]: b for b in saved(page, client)}["k"]["h"] - H) < 0.2
    expect(hint(page)).to_have_count(0)


def test_no_hint_while_nothing_overlaps(editor):
    """Layout (#829): with no block under the Zehnerfeld block, growing it shows no cover hint."""
    client = user()
    page = editor(zeh(y=5), box("t", "text", TEXT, y=240), client=client)
    pick(page, "k")
    more_row(page)
    expect(at(page, "k").locator(".zehnerfeld")).to_be_visible()
    expect(hint(page)).to_have_count(0)
