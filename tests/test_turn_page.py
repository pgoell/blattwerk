"""Turning a page to Quer or Hoch: a centred block stays in the middle, a block that spans the page
stays spanning it, and any other keeps its place. The page is 297 by 210 mm on its side.

The numbers are the page's own: 148.5 is the middle of 297, 282 is 297 less the margin of 15.
"""

import pytest
from playwright.sync_api import expect
from test_hunderterfeld_block import FELD
from test_lock import KINDS
from test_lock_format import OTHER, every
from test_panel_undo import UHR, ZAHLENSTRAHL
from test_rechendreieck import DREIECK
from test_selbstkontrolle_block import SK
from test_suchsel import SUCHSEL
from test_zahlenmauer_size import MAUER
from ui import TEXT, box, doc, user

# The types that stretch across when the page turns: a block spanning the width gets the new width.
STRETCH = {"text", "shape", "line", "ruling", "table", "name", "maths"}
MIDDLE = 148.5
RIGHT = 282


def turn(page, to="Quer", scope=None):
    """The Ansicht panel: the sheet, or only this page, turned to `to`."""
    page.get_by_role("tab", name="Ansicht").click()
    panel = page.locator(".panel")
    if scope:
        panel.get_by_role("button", name=scope).click()
    panel.get_by_role("button", name=to, exact=True).click()


def named(sheet, n=0):
    return {b["id"]: b for b in sheet["pages"][n]["blocks"]}


def test_a_centred_heading_stays_centred(editor):
    client = user()
    page = editor(box("h", "text", TEXT), client=client)
    turn(page, scope="Nur diese Seite")
    quer = doc(page, client)
    h = named(quer)["h"]
    assert h["x"] + h["w"] / 2 == MIDDLE


@pytest.mark.parametrize("kind", [*KINDS, *OTHER])
def test_a_block_of_each_kind_spanning_the_width_stretches_or_stays_centred(editor, kind):
    """Rule 13: every block type. The width is 180 on the upright page, from 15 to 195."""
    client = user()
    page = editor(*every(client, kind), client=client)
    turn(page, scope="Nur diese Seite")
    b = named(doc(page, client))["fest"]
    if kind in STRETCH:
        assert (b["x"], b["x"] + b["w"]) == (15, RIGHT)
    else:
        assert b["w"] == 180 and b["x"] + b["w"] / 2 == MIDDLE


DRAWN = {
    "suchsel": (SUCHSEL, 60),
    "zahlenmauer": (MAUER, 60),
    "rechendreieck": (DREIECK, 60),
    "zahlenstrahl": (ZAHLENSTRAHL, 40),
    "hunderterfeld": (FELD, 180),
    "uhr": (UHR, 110),
    "selbstkontrolle": (SK, 30),
}


@pytest.mark.parametrize("kind", DRAWN)
def test_a_drawn_block_spanning_the_width_keeps_its_size_and_stays_centred(editor, kind):
    """Rule 13, the kinds `every` does not make: their content is drawn to their size, so none
    stretches."""
    client = user()
    props, h = DRAWN[kind]
    page = editor(box("fest", kind, props, w=180, h=h), client=client)
    turn(page, scope="Nur diese Seite")
    b = named(doc(page, client))["fest"]
    assert (b["w"], b["h"], b["x"]) == (180, h, 58.5)


def test_a_block_that_is_neither_keeps_x_and_one_low_on_the_page_comes_up(editor):
    client = user()
    page = editor(
        box("a", "text", TEXT, x=20, w=60),
        box("b", "text", TEXT, z=2, x=20, w=60, y=265),
        client=client,
    )
    turn(page, scope="Nur diese Seite")
    quer = named(doc(page, client))
    assert quer["a"]["x"] == 20
    # The page is 210 high on its side: a 20 mm block at 265 comes up to 190.
    assert quer["b"]["y"] == 190


def test_turning_back_to_hoch_centres_again_and_stretches_back(editor):
    client = user()
    page = editor(box("h", "text", TEXT), box("s", "text", TEXT, z=2, w=180), client=client)
    turn(page)
    quer = named(doc(page, client))
    # The heading centred on the upright page is centred on the Quer page too.
    assert quer["h"]["x"] + quer["h"]["w"] / 2 == MIDDLE
    turn(page, to="Hoch")
    hoch = named(doc(page, client))
    assert hoch["h"]["x"] + hoch["h"]["w"] / 2 == 105
    assert (hoch["s"]["x"], hoch["s"]["w"]) == (15, 180)


def test_alle_seiten_turns_every_page_by_the_same_rule(editor):
    client = user()
    page = editor(
        box("h", "text", TEXT),
        client=client,
        pages=[{"blocks": [box("s", "text", TEXT, w=180)]}],
    )
    turn(page, scope="Alle Seiten")
    quer = doc(page, client)
    assert named(quer, 0)["h"]["x"] + named(quer, 0)["h"]["w"] / 2 == MIDDLE
    s = named(quer, 1)["s"]
    assert (s["x"], s["x"] + s["w"]) == (15, RIGHT)


def test_undo_after_the_turn_gives_the_sheet_back_in_one_step(editor):
    client = user()
    page = editor(
        box("h", "text", TEXT), box("b", "text", TEXT, z=2, x=20, w=60, y=265), client=client
    )
    before = doc(page, client)
    turn(page, scope="Nur diese Seite")
    expect(page.get_by_label("Rückgängig", exact=True)).to_be_enabled()
    assert doc(page, client) != before
    page.get_by_label("Rückgängig", exact=True).click()
    expect(page.get_by_label("Rückgängig", exact=True)).to_be_disabled()
    assert doc(page, client) == before


def test_a_group_of_two_centred_together_moves_as_one_and_keeps_its_size(editor):
    client = user()
    page = editor(
        box("l", "text", TEXT, x=15, w=90, group=["g"]),
        box("r", "text", TEXT, z=2, x=105, w=90, group=["g"]),
        client=client,
    )
    turn(page, scope="Nur diese Seite")
    quer = named(doc(page, client))
    # Two blocks from 15 to 195 are centred on the upright page. They move together by 43.5.
    assert (quer["l"]["x"], quer["l"]["w"]) == (58.5, 90)
    assert (quer["r"]["x"], quer["r"]["w"]) == (148.5, 90)


def test_a_block_that_starts_on_the_margin_plus_one_still_spans(editor):
    """Extra: the start at 16 mm is within the 1 mm the rule allows, so the block stretches."""
    client = user()
    page = editor(box("s", "text", TEXT, x=16, w=178), client=client)
    turn(page, scope="Nur diese Seite")
    s = named(doc(page, client))["s"]
    assert (s["x"], s["x"] + s["w"]) == (16, RIGHT - 1)


def test_a_block_spanning_the_height_stretches_down_on_hoch_to_quer(editor):
    """Extra: a text from 15 to 282 mm high is tall enough to span the upright page, so on the
    shorter Quer page it runs from 15 to 195."""
    client = user()
    page = editor(box("t", "text", TEXT, x=15, w=60, y=15, h=267), client=client)
    turn(page, scope="Nur diese Seite")
    t = named(doc(page, client))["t"]
    assert (t["y"], t["y"] + t["h"]) == (15, 195)
