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
from ui import RULING, TABLE, TEXT, box, doc, pick, user

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
    """Extra: 179 mm is the page less both margins and 1 mm, so from 16 it spans and stretches."""
    client = user()
    page = editor(box("s", "text", TEXT, x=16, w=179), client=client)
    turn(page, scope="Nur diese Seite")
    s = named(doc(page, client))["s"]
    assert (s["x"], s["x"] + s["w"]) == (16, RIGHT)


def test_a_block_spanning_the_height_stretches_down_on_hoch_to_quer(editor):
    """Extra: a text from 15 to 282 mm high is tall enough to span the upright page, so on the
    shorter Quer page it runs from 15 to 195."""
    client = user()
    page = editor(box("t", "text", TEXT, x=15, w=60, y=15, h=267), client=client)
    turn(page, scope="Nur diese Seite")
    t = named(doc(page, client))["t"]
    assert (t["y"], t["y"] + t["h"]) == (15, 195)


def test_a_saved_quer_page_keeps_its_blocks_until_it_is_turned_again(editor):
    """Implied 7: a sheet saved with a Quer page and a block at 15 to 195 on it, as master left it,
    keeps that block where it lies while the teacher works on another page."""
    client = user()
    old = box("alt", "text", TEXT, w=180)
    page = editor(
        box("a", "text", TEXT), client=client, pages=[{"blocks": [old], "landscape": True}]
    )
    page.locator(".dock, .insert").get_by_label("Text", exact=True).click()
    saved = doc(page, client)
    assert saved["pages"][1] == {"blocks": [old], "landscape": True}
    assert len(saved["pages"][0]["blocks"]) == 2


def test_a_page_of_margin_wide_blocks_comes_back_as_it_was_after_quer_and_hoch(
    editor,
):
    """The orchestrator's case: most new blocks start as wide as the space between the margins, so
    Quer widens them all. Turned back, each has its place and size again."""
    client = user()
    long = {**TEXT, "text": "Ein Satz, der auf der schmalen Seite bricht. " * 3}
    page = editor(
        box("t", "text", long, w=180, y=20, h=20),
        box("l", "ruling", RULING, z=2, w=180, y=50, h=40),
        box("n", "name", {}, z=3, w=180, y=100, h=10),
        box("k", "table", TABLE, z=4, w=180, y=120, h=20),
        client=client,
    )
    before = doc(page, client)
    turn(page, scope="Nur diese Seite")
    quer = named(doc(page, client))
    assert all((b["x"], b["w"]) == (15, 267) for b in quer.values())
    turn(page, to="Hoch")
    hoch = doc(page, client)
    assert places(hoch) == places(before)


def places(sheet):
    return [(b["id"], b["x"], b["y"], b["w"], b["h"]) for b in sheet["pages"][0]["blocks"]]


def test_a_margin_wide_circle_keeps_its_shape_and_stays_centred(editor):
    """Review: a circle, a triangle and a star do not stretch into an oval."""
    client = user()
    circle = {"kind": "circle", "fill": "none", "stroke": "#222222", "strokeWidth": 0.5}
    page = editor(box("c", "shape", circle, w=180, h=180, y=15), client=client)
    turn(page, scope="Nur diese Seite")
    c = named(doc(page, client))["c"]
    assert (c["x"], c["w"], c["h"]) == (58.5, 180, 180)


def fields(page, name, labels=("X", "Breite")):
    """The block's X and Breite, or the labels given, in the right panel as a teacher reads them."""
    pick(page, name)
    page.locator(".modes").get_by_role("tab", name="Start").click()
    geo = page.locator(".geo")
    expect(geo).to_be_visible()
    return {
        label: float(geo.get_by_label(label, exact=True).input_value().replace(",", "."))
        for label in labels
    }


@pytest.mark.parametrize("x", [20, 25, 30])
def test_issue_613_a_block_that_lands_off_the_margin_spans_the_turned_page(editor, x):
    """#613: a new block lands 5 mm on from the one under it, so 180 wide it starts at 20, 25 or 30.
    It still spans the width: it keeps its start and grows by 87."""
    client = user()
    page = editor(box("t", "text", TEXT, x=x, w=180, y=55), client=client)
    turn(page)
    assert fields(page, "t") == {"X": x, "Breite": 267}


@pytest.mark.parametrize(
    "kind, props, h",
    [("uhr", UHR, 110), ("rechendreieck", DREIECK, 60), ("selbstkontrolle", SK, 30)],
)
def test_issue_613_a_block_one_step_off_the_middle_stays_one_step_off(editor, kind, props, h):
    """#613: a centred block lands 5 mm off the middle. It keeps that 5 mm when the page turns."""
    client = user()
    page = editor(box("b", kind, props, x=20, w=180, h=h, y=55), client=client)
    turn(page)
    assert fields(page, "b") == {"X": 63.5, "Breite": 180}


def test_issue_613_a_heading_one_step_off_the_middle_keeps_its_offset(editor):
    client = user()
    page = editor(box("h", "text", TEXT, x=50, w=120, y=35), client=client)
    turn(page)
    f = fields(page, "h")
    assert f["X"] + f["Breite"] / 2 == 148.5 + 5


@pytest.mark.parametrize("x, w", [(15, 150), (15, 160), (24, 168)])
def test_issue_613_a_block_off_the_middle_by_other_than_a_paste_step_stays_at_the_left(
    editor, x, w
):
    """Edge: the middle is 0, 5, 10 or 15 mm right of the page's middle, and a block at 15, 150 wide
    or 160 wide is not. At 24 with 168 its middle is 3 mm off, so it stays too."""
    client = user()
    page = editor(box("l", "text", TEXT, x=x, w=w, y=55), client=client)
    turn(page)
    assert fields(page, "l") == {"X": x, "Breite": w}


@pytest.mark.parametrize(
    "kind, props, h, x, w",
    [("text", TEXT, 20, 20, 180), ("text", TEXT, 20, 50, 120), ("uhr", UHR, 110, 20, 180)],
)
def test_issue_613_turned_back_upright_the_offset_blocks_have_their_start_places(
    editor, kind, props, h, x, w
):
    """Edge: Quer, then Hoch: a block that was pushed off the middle comes back to its start."""
    client = user()
    page = editor(box("b", kind, props, x=x, w=w, h=h, y=55), client=client)
    turn(page)
    turn(page, to="Hoch")
    assert fields(page, "b") == {"X": x, "Breite": w}


def test_issue_613_a_right_column_keeps_its_x_turned_to_quer_and_back(editor):
    """#613: a text on the right, from 110 to 195, is not centred, so Quer and back keep its X."""
    client = user()
    page = editor(box("r", "text", TEXT, x=110, w=85, y=55), client=client)
    turn(page)
    assert fields(page, "r") == {"X": 110, "Breite": 85}
    turn(page, to="Hoch")
    assert fields(page, "r") == {"X": 110, "Breite": 85}


def test_issue_613_a_text_at_15_and_165_wide_stays_on_quer(editor):
    """#613: from 15 to 180 is 7.5 mm left of the page's middle: not a paste step, so it stays."""
    client = user()
    page = editor(box("t", "text", TEXT, x=15, w=165, y=55), client=client)
    turn(page)
    assert fields(page, "t") == {"X": 15, "Breite": 165}


def test_issue_613_a_tall_text_and_lineatur_keep_their_height_turned_back_upright(editor):
    """#613: nothing stretches down the page. A 180 mm high block at Y 25 keeps its height."""
    client = user()
    page = editor(
        box("t", "text", TEXT, x=15, w=60, y=25, h=180),
        box("l", "ruling", RULING, z=2, x=100, w=60, y=25, h=180),
        client=client,
    )
    turn(page)
    turn(page, to="Hoch")
    assert fields(page, "t", ("Höhe",)) == {"Höhe": 180}
    assert fields(page, "l", ("Höhe",)) == {"Höhe": 180}


def test_issue_613_a_block_at_15_and_170_wide_comes_back_to_15_after_hoch(editor):
    """#613: a block from 15 to 185 is not centred on Quer, so Hoch and Quer give its X 15 back."""
    client = user()
    page = editor(box("b", "text", TEXT, x=15, w=170, y=55), client=client)
    turn(page)
    turn(page, to="Hoch")
    turn(page)
    assert fields(page, "b") == {"X": 15, "Breite": 170}
