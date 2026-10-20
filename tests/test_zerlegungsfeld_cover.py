"""A Zerlegungsfeld grown over a block says so, and moves nothing; near the paper's foot it grows past the
margin and says so (#827, as the Malquadrat #826).

The hint texts are copied from the Malquadrat's pattern and must be checked against the Zerlegungsfeld's own panel and
drawing once the block exists: a hint whose words differ from them is a wrong test, not a wrong block.
"""

import pytest
from playwright.sync_api import expect
from test_gaps import panel, step
from ui import TEXT, at, box, pick, saved, user

ZF = {
    "count": 6,
    "columns": 3,
    "op": "+",
    "max": 20,
    "step": "zehner",
    "big": False,
    "task": "task",
    "seed": 7,
}
FOOT = "Das Zerlegungsfeld ragt unten über den Rand."
COVER = (
    "Das Zerlegungsfeld liegt über einem anderen Block. "
    "Verschiebe ihn oder mache das Zerlegungsfeld kleiner."
)
H = 128.9  # the default height: 111 * 180 / 155


@pytest.fixture
def editor(editor):
    """The editor with its panel open, where the Zerlegungsfeld's settings are."""

    def start(*blocks, **more):
        return editor(*blocks, theme="", **more)

    return start


def zf(name="k", y=5, **more):
    """A Zerlegungsfeld block of 180 by 128.9 mm over the blocks of z 1."""
    return box(name, "zerlegungsfeld", ZF, z=2, w=180, h=H, y=y, **more)


def hint(page):
    return page.locator('p[data-cover="zerlegungsfeld"]')


def foot(page):
    return page.locator('p[data-foot="haus"], p[data-foot="over"]')


def more_row(page):
    """Presses Eine Aufgabe mehr three times, and waits for the save: 3 tasks make one more row of 3 columns, so the
    block grows."""
    for _ in range(3):
        step(page, lambda: panel(page, "Eine Aufgabe mehr").click())


def undo_row(page):
    """Takes back the three presses of more_row: each press is its own undo step."""
    for _ in range(3):
        step(page, lambda: page.get_by_label("Rückgängig", exact=True).first.click())


def test_a_zerlegungsfeld_near_the_foot_grows_past_it_and_keeps_its_task_size(editor):
    """Layout (#827): one more row takes a block at y 95 past the margin's foot but not past the paper: the
    stored height grows, the task size stays, and the foot hint says so."""
    # y 95 puts the grown block (about 196 mm high) between the margin's foot (282 mm) and the paper's edge (297 mm).
    client = user()
    page = editor(zf(y=95), box("t", "text", TEXT, x=150, y=80, w=40, h=30), client=client)
    pick(page, "k")
    before = at(page, "k").locator("g.task").first.bounding_box()["width"]
    more_row(page)
    stored = {b["id"]: b for b in saved(page, client)}
    assert stored["k"]["h"] > H and 282 < 95 + stored["k"]["h"] <= 297, stored["k"]
    assert stored["t"]["x"] == 150 and stored["t"]["y"] == 80, stored["t"]
    after = at(page, "k").locator("g.task").first.bounding_box()["width"]
    assert abs(after - before) <= 0.01 * before, (before, after)
    expect(foot(page).filter(has_text=FOOT)).to_be_visible()


def test_one_undo_takes_the_grown_height_and_the_foot_hint_back(editor):
    """Layout (#827): one more row takes a block past the foot; one undo takes the grown height and the foot hint
    back, and the stored height is 128.9 again."""
    client = user()
    page = editor(zf(y=95), box("t", "text", TEXT, x=150, y=80, w=40, h=30), client=client)
    pick(page, "k")
    expect(foot(page).filter(has_text=FOOT)).to_have_count(0)
    more_row(page)
    expect(foot(page).filter(has_text=FOOT)).to_be_visible()
    assert {b["id"]: b for b in saved(page, client)}["k"]["h"] > H
    undo_row(page)
    assert abs({b["id"]: b for b in saved(page, client)}["k"]["h"] - H) < 0.2
    expect(foot(page).filter(has_text=FOOT)).to_have_count(0)


def test_growing_over_a_text_warns_and_moves_nothing(editor):
    """Layout (#827): one more row grows a block over a text: the text stays and the hint says the block covers it."""
    client = user()
    page = editor(zf(y=5), box("t", "text", TEXT, y=140), client=client)
    pick(page, "k")
    expect(hint(page)).to_have_count(0)
    more_row(page)
    stored = {b["id"]: b for b in saved(page, client)}
    assert stored["k"]["h"] > H, stored["k"]
    assert stored["t"]["y"] == 140, stored["t"]
    expect(hint(page)).to_be_visible()
    expect(hint(page)).to_have_text(COVER)


def test_one_undo_takes_the_height_and_the_hint_back(editor):
    """Layout (#827): one undo takes the grown height and the cover hint back, and the stored height is 128.9
    again."""
    client = user()
    page = editor(zf(y=5), box("t", "text", TEXT, y=140), client=client)
    pick(page, "k")
    more_row(page)
    expect(hint(page)).to_be_visible()
    undo_row(page)
    assert abs({b["id"]: b for b in saved(page, client)}["k"]["h"] - H) < 0.2
    expect(hint(page)).to_have_count(0)


def test_no_hint_while_nothing_overlaps(editor):
    """Layout (#827): with no block under the Zerlegungsfeld, growing it shows no cover hint."""
    client = user()
    page = editor(zf(y=5), box("t", "text", TEXT, y=240), client=client)
    pick(page, "k")
    more_row(page)
    expect(at(page, "k").locator(".zerlegungsfeld")).to_be_visible()
    expect(hint(page)).to_have_count(0)
