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


def uhr_fits(page):
    field(page, "Uhren").fill("3")


# kind: (props, width, height, the Y that a few "more" presses pass the paper's edge from, the "more" press, a press that fits)
CASES = {
    "zahlenhaus": (HAUS, 120, 55, 240, haus_more, haus_fits),
    "zahlenmauer": ({**MAUER, "columns": 1}, 180, 60, 230, mauer_more, mauer_fits),
    "rechendreieck": (DREIECK, 180, 50, 230, dreieck_more, dreieck_fits),
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
