"""A line as a ruler (#837): centimetre ticks with numbers on one side, millimetres when asked.

Länge in cm and Drehung are typed in the panel. The print draws the same ticks as the editor.
"""

import pytest
from pixels import over, screen_and_print
from playwright.sync_api import expect
from test_feed_print import printed, sheet_id
from test_fields import enter, field
from ui import LINE, at, box, pick, saved, user

# How far a tick reaches, in mm: the same lengths as REACH in frontend/src/ruler.ts.
CM, HALF, MM = 4, 2.5, 1.5
MARKS = """el => ({
    flip: el.getAttribute("transform") ?? "",
    lines: [...el.querySelectorAll("line")].map((l) => ({
        kind: l.getAttribute("class"),
        x: +l.getAttribute("x1"),
        y1: +l.getAttribute("y1"),
        y2: +l.getAttribute("y2"),
    })),
    numbers: [...el.querySelectorAll("text.n")].map((t) => t.textContent),
})"""


def marks(page, name="a"):
    """The ruler's ticks and numbers, in the line's own millimetres.

    The editor names a block with data-id, the print page with data-block.
    """
    block = page.locator(f'.block[data-id="{name}"], .block[data-block="{name}"]')
    return block.locator("svg g.ruler").evaluate(MARKS)


def ruler(w=50, h=0, **props):
    return box("a", "shape", {**LINE, "ruler": True, **props}, x=40, y=80, w=w, h=h)


def test_centimetre_ticks_and_numbers_stand_on_one_side(editor):
    """50 mm: ticks at each centimetre, numbered 0 to 5, and none of them crosses the line."""
    page = editor(ruler(), client=user())
    got = marks(page)
    assert got["flip"] == ""
    assert got["lines"] == [
        {"kind": "cm", "x": x, "y1": 0, "y2": -CM} for x in (0, 10, 20, 30, 40, 50)
    ]
    assert got["numbers"] == ["0", "1", "2", "3", "4", "5"]


def test_millimetres_are_shorter_ticks_on_the_same_side(editor):
    """Every millimetre gets a tick, a half centimetre a longer one, and none of them crosses the line."""
    page = editor(ruler(mm=True, w=20), client=user())
    got = marks(page)
    assert [line["x"] for line in got["lines"]] == list(range(21))
    by = {line["kind"]: line["y2"] for line in got["lines"]}
    assert by == {"cm": -CM, "half": -HALF, "mm": -MM}
    assert all(line["y1"] == 0 and line["y2"] < 0 for line in got["lines"])


def test_a_leftward_line_mirrors_the_ruler_so_the_numbers_stay_upright(editor):
    """Pointing left, the ticks stay on the side that reads upright and the numbers still run from 0."""
    page = editor(ruler(**{"from": "ne"}), client=user())
    turned = marks(page)
    assert turned["flip"] == "scale(1 -1)"
    assert turned["numbers"] == ["0", "1", "2", "3", "4", "5"]
    assert all(line["y2"] == -CM for line in turned["lines"])


def test_lineal_length_and_turn_are_typed(editor):
    """Lineal and Millimeter switch on, Länge sets the centimetres, and Drehung turns the ends."""
    client = user()
    # 1 mm of height is enough to click. The length is a hair over 5 cm, and 8 cm lands on the stored hundredths.
    page = editor(box("a", "shape", LINE, x=40, y=80, w=50, h=1), client=client)
    pick(page, "a")
    lineal = page.locator(".panel").get_by_role("button", name="Lineal", exact=True)
    expect(lineal).to_have_attribute("aria-pressed", "false")
    lineal.click()
    expect(lineal).to_have_attribute("aria-pressed", "true")
    expect(at(page, "a").locator("svg g.ruler text.n")).to_have_count(6)
    milli = page.locator(".panel").get_by_role("button", name="Millimeter", exact=True)
    expect(milli).to_have_attribute("aria-pressed", "false")
    milli.click()
    expect(milli).to_have_attribute("aria-pressed", "true")
    expect(at(page, "a").locator("svg g.ruler line")).to_have_count(51)
    length = page.locator(".panel").get_by_label("Länge in cm", exact=True)
    length.fill("8")
    expect(length).to_have_value("8")
    # Ticks cover every whole millimetre of the length the line is drawn at.
    span = float(at(page, "a").locator("svg > g > line").first.get_attribute("x2"))
    got = marks(page)
    assert [line["x"] for line in got["lines"]] == list(range(int(span) + 1))
    assert got["numbers"][0] == "0"
    assert got["numbers"][-1] == str(int(span) // 10)
    enter(page, "Drehung", "90")
    expect(field(page, "Drehung")).to_have_value("90")
    (block,) = saved(page, client)
    assert block["w"] == pytest.approx(0, abs=0.02)
    assert block["h"] == pytest.approx(80, abs=0.02)
    assert block["props"]["ruler"] is True
    assert block["props"]["mm"] is True
    assert block["props"]["from"] == "nw"


def test_the_print_draws_the_same_ticks(editor, browser, server):
    """The print page draws the ruler the editor draws."""
    page = editor(ruler(mm=True), client=user())
    screen = marks(page)
    paper = printed(browser, server, sheet_id(page))
    assert marks(paper) == screen
    paper.context.close()


def test_the_pdf_matches_the_ruler_on_screen(editor, browser, server):
    """The PDF shows the same ruler the editor shows."""
    client = user()
    page = editor(ruler(mm=True), client=client)
    assert not over(*screen_and_print(browser, server, client, sheet_id(page)))
