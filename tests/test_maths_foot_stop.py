"""Anzahl stops at the foot of the page, on screen and in the pdf."""

import math

import httpx
import pypdfium2
import pytest
from playwright.sync_api import expect
from test_feed_print import sheet_id
from test_maths_fit import inside
from test_maths_foot import (
    FOOT,
    asked,
    click,
    height,
    on_sheet,
    panel,
    refusal,
    tasks,
)
from ui import (
    at,
    box,
    maths,
    pick,
    user,
)


def test_a1_anzahl_stops_at_the_foot_with_neighbour_families(editor):
    """A1: one family more would end the block below the foot: the count stays, a line says why."""
    client = user()
    props = maths(client, ops=["+", "-"], max=100, family="neighbour", count=24, columns=3, size=14)
    page = editor(box("m", "maths", props, y=20, h=height(props)), client=client)
    pick(page, "m")
    page.get_by_label("Eine Aufgabe mehr").click()
    refusal(page)
    expect(tasks(page).first).to_have_text("24 Familien")
    on_sheet(page, "m")
    inside(page, "m")


@pytest.mark.parametrize(
    "case, props, action, grows",
    [
        pytest.param(
            "row-more", {"format": "row"}, click("Eine Aufgabe mehr"), True, id="row-more"
        ),
        pytest.param(
            "gap-more", {"format": "gap"}, click("Eine Aufgabe mehr"), True, id="gap-more"
        ),
        pytest.param(
            "compare-more",
            {"format": "compare"},
            click("Eine Aufgabe mehr"),
            True,
            id="compare-more",
        ),
        pytest.param(
            "written-more",
            {"format": "written"},
            click("Eine Aufgabe mehr"),
            True,
            id="written-more",
        ),
        pytest.param(
            "row-fewer-columns",
            {"format": "row"},
            click("Eine Spalte weniger"),
            True,
            id="row-fewer-columns",
        ),
        pytest.param(
            "row-bigger", {"format": "row"}, click("Schrift größer"), True, id="row-bigger"
        ),
        pytest.param(
            "row-written", {"format": "row"}, panel("Schriftlich"), True, id="row-written"
        ),
        pytest.param(
            "row-neighbour",
            {"format": "row", "ops": ["+"]},
            lambda page: page.get_by_label("Aufgabenfamilien").select_option("neighbour"),
            True,
            id="row-neighbour",
        ),
        pytest.param(
            "written-division",
            {"format": "written", "ops": ["+"]},
            panel(":"),
            True,
            id="written-division",
        ),
        pytest.param(
            "written-room",
            {"format": "written", "ops": ["/"], "max": 10},
            asked(lambda page: page.get_by_label("Zahlenraum").select_option("1000000")),
            True,
            id="written-room",
        ),
        pytest.param(
            "written-rest",
            {"format": "written", "ops": ["/"]},
            asked(panel("Mit Rest")),
            False,
            id="written-rest",
        ),
        pytest.param(
            "written-roll",
            {"format": "written", "ops": ["-", "/"]},
            asked(panel("Neu würfeln")),
            False,
            id="written-roll",
        ),
    ],
)
def test_a2_no_panel_change_pushes_the_block_past_the_foot(editor, case, props, action, grows):
    """A2: each change from the panel that would grow the block past the foot is refused."""
    client = user()
    mine = maths(
        client,
        ops=props.get("ops", ["+", "-"]),
        max=props.get("max", 100),
        count=12,
        columns=3,
        size=14,
        format=props["format"],
    )
    # The block's foot is 1 mm above the page's: the first line more passes it.
    page = editor(box("m", "maths", mine, y=FOOT - height(mine) - 1, h=height(mine)), client=client)
    pick(page, "m")
    action(page)
    if grows:
        refusal(page)
    else:
        # The new exercises are drawn: each of the 12 divisions has its svg.
        expect(at(page, "m").locator("svg")).to_have_count(12)
    on_sheet(page, "m")
    inside(page, "m")


def test_a3_at_the_stop_the_pdf_has_every_task(editor, server):
    """A3: the block stops at 12 tasks at the foot, and the PDF prints all 12."""
    client = user()
    props = maths(
        client, ops=["+", "-"], max=100, count=12, columns=3, size=14, format="row", numbering="1"
    )
    page = editor(
        box("m", "maths", props, y=FOOT - height(props) - 1, h=height(props)), client=client
    )
    pick(page, "m")
    page.get_by_label("Eine Aufgabe mehr").click()
    refusal(page)
    cookie = {"Cookie": f"session={client.cookies['session']}"}
    res = httpx.get(f"{server}/api/sheets/{sheet_id(page)}/pdf", headers=cookie, timeout=60)
    assert res.status_code == 200
    doc = pypdfium2.PdfDocument(res.content)
    assert len(doc) == 1
    text = doc[0].get_textpage().get_text_range()
    # Each task of a row has one "=": the PDF holds as many as the screen has tasks.
    assert text.count("=") == at(page, "m").locator(".maths > div").count() == 12, text[:300]


def test_i2_the_line_goes_when_there_is_room_again(editor):
    """I2: after a refusal, one column more makes room: the line goes and one task more works."""
    client = user()
    props = maths(client, ops=["+", "-"], max=100, count=12, columns=3, size=14, format="row")
    page = editor(
        box("m", "maths", props, y=FOOT - height(props) - 1, h=height(props)), client=client
    )
    pick(page, "m")
    page.get_by_label("Eine Aufgabe mehr").click()
    refusal(page)
    page.get_by_label("Eine Spalte mehr").click()
    expect(page.locator('[data-foot="full"]')).to_be_hidden()
    page.get_by_label("Eine Aufgabe mehr").click()
    expect(tasks(page).first).to_have_text("13 Aufgaben")


def test_i3_a_block_below_the_edge_says_so_and_can_still_shrink(editor):
    """I3: a block that ends below the edge says so, and one task less still works."""
    client = user()
    props = maths(client, ops=["+", "-"], max=100, count=12, columns=3, size=14, format="row")
    page = editor(box("m", "maths", props, y=280, h=height(props)), client=client)
    pick(page, "m")
    expect(page.locator('[data-foot="over"]')).to_be_visible()
    before = at(page, "m").bounding_box()["height"]
    # Four columns take three lines in place of four: the block gets shorter.
    page.get_by_label("Eine Spalte mehr").click()
    expect(tasks(page).nth(1)).to_have_text("4 Spalten")
    assert at(page, "m").bounding_box()["height"] < before - 1, "the block did not get shorter"


def test_a2_a_block_sized_by_hand_does_not_grow_past_the_foot(editor):
    """A2 by hand: a block of 20 mm counts growth from its own foot: one column more is refused."""
    client = user()
    props = maths(client, ops=["+", "-"], max=100, count=12, columns=3, size=14, format="row")
    page = editor(box("m", "maths", props, y=270, h=20), client=client)
    pick(page, "m")
    page.get_by_label("Eine Spalte mehr").click()
    refusal(page)
    on_sheet(page, "m")


def test_i7_a_turned_block_stops_at_its_lowest_corner(editor):
    """I7: a turned block counts its lowest corner, so one more task is refused at the foot."""
    client = user()
    props = maths(client, ops=["+", "-"], max=100, count=12, columns=3, size=14, format="row")
    h, w = height(props), 180
    s, c = math.sin(math.radians(30)), math.cos(math.radians(30))
    # lowest = y + h/2 + (w|sin| + h|cos|)/2 ; put it at 296 mm.
    y = (FOOT - 1) - h / 2 - (w * s + h * c) / 2
    page = editor(box("m", "maths", props, y=round(y, 2), h=h, angle=30), client=client)
    pick(page, "m")
    page.get_by_label("Eine Aufgabe mehr").click()
    refusal(page)
    expect(tasks(page).first).to_have_text("12 Aufgaben")
