"""A maths drawing that would grow past the paper's edge is refused, and the panel says why (#911).

The block sits low on the page, one column, so a few presses of its "more" control pass the paper's
edge at 297 mm. The refused press keeps the props and the height, makes no undo step and shows the
paper hint; a press that fits takes the hint away again.
"""

import pytest
from playwright.sync_api import expect
from test_gaps import panel, step
from test_rechendreieck_size import DREIECK
from test_uhr_grow import UHR
from test_zahlenhaus_cover import HAUS
from test_zahlenkette_cover import KETTE
from test_zahlenmauer_size import MAUER
from ui import box, pick, saved, user


@pytest.fixture
def editor(editor):
    """The editor with its panel open, where the block's settings are."""

    def start(*blocks, **more):
        return editor(*blocks, theme="", **more)

    return start


def field(page, label):
    return page.locator(".panel").get_by_label(label, exact=True)


def paper_hint(page):
    return page.locator('p[data-foot="paper"]')


def stored(page, client):
    """The block as the server holds it."""
    return {b["id"]: b for b in saved(page, client)}["b"]


def refused_after(page, client, more):
    """Presses `more` until the panel refuses one. Returns the stored block after each press, so the
    last one is the refused press's state."""
    states = [stored(page, client)]
    for i in range(40):
        more(page, i)
        page.wait_for_timeout(1500)
        states.append(stored(page, client))
        if paper_hint(page).is_visible():
            return states
    raise AssertionError("the panel never refused a press")


def haus_more(page, i):
    field(page, "Stockwerke").select_option(str(5 + i))


def mauer_more(page, i):
    panel(page, "Eine Mauer mehr").click()


def dreieck_more(page, i):
    panel(page, "Ein Dreieck mehr").click()


def uhr_more(page, i):
    field(page, "Uhren").fill(str(5 + i))


# A press that fits: a value whose height is no more than the stored one, so it is not refused.
def haus_fits(page):
    field(page, "Stockwerke").select_option("3")


def mauer_fits(page):
    panel(page, "Eine Spalte mehr").click()


def dreieck_fits(page):
    panel(page, "Ein Dreieck weniger").click()


def kette_more(page, i):
    panel(page, "Eine Kette mehr").click()


def kette_fits(page):
    panel(page, "Eine Kette weniger").click()


PFEIL = {
    "count": 4,
    "columns": 2,
    "boxes": 4,
    "max": 20,
    "ops": ["+", "-"],
    "arrows": "one",
    "given": "start",
    "drawOps": True,
    "seed": 7,
}


def pfeil_more(page, i):
    panel(page, "Ein Pfeilbild mehr").click()


def pfeil_fits(page):
    panel(page, "Ein Pfeilbild weniger").click()


OPERATORFELD = {
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


def of_more(page, i):
    panel(page, "Ein Operatorfeld mehr").click()


def of_fits(page):
    panel(page, "Ein Operatorfeld weniger").click()


RECHENRAD = {
    "count": 2,
    "columns": 2,
    "rings": 2,
    "segments": 8,
    "max": 20,
    "op": "+",
    "task": "outer",
    "seed": 7,
}


def rr_more(page, i):
    panel(page, "Ein Rechenrad mehr").click()


def rr_fits(page):
    panel(page, "Ein Rechenrad weniger").click()


RECHENTABELLE = {
    "count": 2,
    "columns": 2,
    "rows": 4,
    "cols": 4,
    "op": "+",
    "max": 20,
    "carry": ["either", "either"],
    "reihen": [2, 4, 5, 10],
    "order": "related",
    "first": "all",
    "hideRows": 0,
    "hideCols": 0,
    "tint": "none",
    "seed": 7,
}


def rt_more(page, i):
    panel(page, "Eine Zeile mehr").click()


def rt_fits(page):
    panel(page, "Eine Zeile weniger").click()


MAGISCHES_QUADRAT = {
    "count": 2,
    "columns": 2,
    "size": 3,
    "max": 20,
    "given": 4,
    "showSum": False,
    "seed": 7,
}


def mq_more(page, i):
    panel(page, "Ein Quadrat mehr").click()


def mq_fits(page):
    panel(page, "Ein Quadrat weniger").click()


MALQUADRAT = {
    "count": 2,
    "columns": 2,
    "size": 3,
    "op": "*",
    "reihen": [2, 3, 4, 5, 6, 7, 8, 9],
    "max": 20,
    "task": "factors",
    "seed": 7,
}


def ml_more(page, i):
    panel(page, "Ein Malquadrat mehr").click()


def ml_fits(page):
    panel(page, "Ein Malquadrat weniger").click()


ZERLEGUNGSFELD = {
    "count": 6,
    "columns": 3,
    "op": "+",
    "max": 20,
    "step": "zehner",
    "big": False,
    "task": "task",
    "seed": 7,
}


def zf_more(page, i):
    panel(page, "Eine Aufgabe mehr").click()


def zf_fits(page):
    panel(page, "Eine Aufgabe weniger").click()


def uhr_fits(page):
    field(page, "Uhren").fill("3")
    field(page, "Uhren").blur()


# kind: (props, width, height, the Y that a few "more" presses pass the paper's edge from, the "more" press, a press that fits)
CASES = {
    "zahlenhaus": (HAUS, 120, 55, 240, haus_more, haus_fits),
    "zahlenmauer": ({**MAUER, "columns": 1}, 180, 60, 230, mauer_more, mauer_fits),
    "rechendreieck": (DREIECK, 180, 50, 230, dreieck_more, dreieck_fits),
    "zahlenkette": (KETTE, 180, 39, 230, kette_more, kette_fits),
    "pfeilbild": (PFEIL, 180, 53.9, 230, pfeil_more, pfeil_fits),
    "operatorfeld": (
        OPERATORFELD,
        180,
        85.99,
        110,
        of_more,
        of_fits,
    ),  # y 110, see test_operatorfeld_cover.py
    "rechenrad": (
        RECHENRAD,
        180,
        85.53,
        110,
        rr_more,
        rr_fits,
    ),  # y 110, see test_rechenrad_cover.py
    "rechentabelle": (
        RECHENTABELLE,
        180,
        84.22,
        190,
        rt_more,
        rt_fits,
    ),  # y 190: the default height, one more row (16.5 mm) passes the paper's foot at 282 mm
    # y 110: one square (count 1 to 2) keeps the height, the next (2 to 3, two lines, about 206 mm) passes the paper's edge.
    "magischesquadrat": (MAGISCHES_QUADRAT, 180, 96.52, 110, mq_more, mq_fits),
    # y 110: two squares (2 to 3, two lines, about 193 mm tall) pass the paper's edge.
    "malquadrat": (MALQUADRAT, 180, 93.98, 110, ml_more, ml_fits),
    # y 110: 110 + 128.9 fits; one more row of tasks (6 to 9, about 196 mm tall) passes the paper's edge.
    "zerlegungsfeld": (ZERLEGUNGSFELD, 180, 128.9, 110, zf_more, zf_fits),
    "uhr": (UHR, 180, 58.5, 230, uhr_more, uhr_fits),
}


@pytest.mark.parametrize("kind", list(CASES))
def test_911_a_press_past_the_paper_edge_is_refused_and_undo_takes_back_the_last_accepted(
    editor, kind
):
    """#911: a press that would grow the block below the paper's edge keeps the props and the height,
    shows the paper hint, and one undo takes back the last accepted change, not the refused press."""
    client = user()
    props, w, h, y, more, fits = CASES[kind]
    page = editor(box("b", kind, props, w=w, h=h, y=y), client=client)
    pick(page, "b")
    init = stored(page, client)
    step(page, lambda: fits(page))
    states = refused_after(page, client, more)
    before, refused = states[-2], states[-1]
    assert refused["props"] == before["props"] and refused["h"] == before["h"], (before, refused)
    expect(paper_hint(page)).to_be_visible()
    # The last accepted change is the state before the refused press's predecessor, or the fitting press.
    target = states[-3] if len(states) >= 3 else init
    step(page, lambda: page.get_by_label("Rückgängig", exact=True).first.click())
    undone = stored(page, client)
    assert undone["props"] == target["props"] and undone["h"] == target["h"], (target, undone)


@pytest.mark.parametrize("kind", list(CASES))
def test_911_after_a_refused_press_a_press_that_fits_takes_the_paper_hint_away(editor, kind):
    """#911: once a press is refused, a press that fits makes the paper hint go."""
    client = user()
    props, w, h, y, more, fits = CASES[kind]
    page = editor(box("b", kind, props, w=w, h=h, y=y), client=client)
    pick(page, "b")
    refused_after(page, client, more)
    expect(paper_hint(page)).to_be_visible()
    step(page, lambda: fits(page))
    expect(paper_hint(page)).to_have_count(0)


def test_911_a_fewer_press_on_a_block_capped_by_master_is_taken(editor):
    """#911: a Zahlenmauer master capped at the foot (1 column, 6 walls, 50 mm) takes "Eine Mauer weniger"."""
    client = user()
    page = editor(
        box("b", "zahlenmauer", {**MAUER, "columns": 1, "count": 6}, w=180, h=50, y=230),
        client=client,
    )
    pick(page, "b")
    step(page, lambda: panel(page, "Eine Mauer weniger").click())
    block = stored(page, client)
    assert block["props"]["count"] == 5, block
    # Fewer walls need no more room than before: the block keeps its height and stays on the paper.
    assert block["h"] == 50, block
    expect(paper_hint(page)).to_have_count(0)


def test_911_a_typed_count_refused_after_a_taken_one_brings_the_old_height_back(editor):
    """#911, review: "8" grows the Uhr, then "1" "2" is refused past the paper: count and height go back to
    the 4 clocks and 58.5 mm the block had when the field got focus."""
    client = user()
    page = editor(box("b", "uhr", UHR, w=180, h=58.5, y=150), client=client)
    pick(page, "b")
    uhren = field(page, "Uhren")
    uhren.click()
    page.keyboard.press("Control+A")
    step(page, lambda: uhren.press_sequentially("8"))
    assert stored(page, client)["h"] > 58.5
    page.keyboard.press("Control+A")
    uhren.press_sequentially("12")
    expect(paper_hint(page)).to_be_visible()
    for _ in range(50):
        block = stored(page, client)
        if block["props"]["count"] == 4 and block["h"] == 58.5:
            break
        page.wait_for_timeout(100)
    assert block["props"]["count"] == 4 and block["h"] == 58.5, block


def test_911_a_typed_count_past_the_paper_is_refused_and_the_field_goes_back(editor):
    """#911: typing "1" then "12" into Uhren takes 1, refuses 12, and the stored count goes back to 4;
    the hint stays, and the field shows 4 after the blur."""
    client = user()
    page = editor(box("b", "uhr", UHR, w=180, h=58.5, y=230), client=client)
    pick(page, "b")
    field(page, "Uhren").click()
    page.keyboard.press("Control+A")
    field(page, "Uhren").press_sequentially("12")
    expect(paper_hint(page)).to_be_visible()
    assert stored(page, client)["props"]["count"] == 4, stored(page, client)
    page.keyboard.press("Tab")
    expect(field(page, "Uhren")).to_have_value("4")


def test_911_undo_of_an_earlier_change_takes_the_paper_hint_away(editor):
    """#911: after a refused press, one undo of an earlier accepted change takes the hint away."""
    client = user()
    page = editor(box("b", "zahlenmauer", MAUER, w=180, h=60, y=230), client=client)
    pick(page, "b")
    step(page, lambda: panel(page, "Eine Spalte mehr").click())
    refused_after(page, client, mauer_more)
    expect(paper_hint(page)).to_be_visible()
    step(page, lambda: page.get_by_label("Rückgängig", exact=True).first.click())
    expect(paper_hint(page)).to_have_count(0)


def test_911_moving_the_block_up_takes_the_paper_hint_away(editor):
    """#911: after a refused press, moving the block up through the panel's Y field takes the hint away."""
    client = user()
    page = editor(box("b", "zahlenmauer", MAUER, w=180, h=60, y=230), client=client)
    pick(page, "b")
    refused_after(page, client, mauer_more)
    expect(paper_hint(page)).to_be_visible()
    y = page.locator(".geo").get_by_label("Y", exact=True)
    step(page, lambda: (y.fill("100"), y.press("Enter")))
    expect(paper_hint(page)).to_have_count(0)
