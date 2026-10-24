"""The brush carries a Lineatur's script, Nachspuren and line colour, and a table's line colour."""

from playwright.sync_api import expect
from test_painter import (
    GREY,
    RED_LINE,
    held,
    paint,
    whole,
)
from ui import (
    RULING,
    TABLE,
    at,
    box,
    pick,
    user,
)


def test_a_lineatur_carries_its_script(editor):
    client = user()
    page = editor(
        box("a", "ruling", {**RULING, "font": "grund"}),
        box("b", "ruling", {**RULING, "text": "du"}, z=2),
        box("c", "ruling", RULING, z=3),
        box("d", "ruling", {**RULING, "font": "va"}, z=4),
        client=client,
    )
    paint(page, "a", "b")
    # A Lineatur with no script of its own is in print, and so is the one it paints.
    paint(page, "c", "d")
    now = held(page, client)
    assert now["b"] == {**RULING, "text": "du", "font": "grund"}
    assert now["d"] == RULING


def test_a_lineatur_carries_its_colour(editor):
    client = user()
    page = editor(
        box("a", "ruling", {**RULING, "color": "#ff0000"}),
        box("b", "ruling", {**RULING, "kind": "l1", "trace": True}, z=2),
        client=client,
    )
    paint(page, "a", "b")
    expect(at(page, "b").locator("svg.ruling")).to_have_attribute("stroke", "#ff0000")
    # The source has no Nachspuren, so the painted one loses its own.
    assert held(page, client)["b"] == {**RULING, "kind": "l1", "color": "#ff0000"}


def test_a_lineatur_carries_nachspuren(editor):
    client = user()
    karo = {"kind": "k5", "color": "#222222", "text": "du"}
    page = editor(
        box("a", "ruling", {**RULING, "text": "ich", "trace": True}),
        box("b", "ruling", {**RULING, "text": "du"}, z=2),
        box("k", "ruling", karo, z=3),
        box("c", "ruling", {**RULING, "kind": "l1", "text": "wir"}, z=4),
        client=client,
    )
    expect(at(page, "b").locator(".written")).not_to_have_css("color", GREY)
    paint(page, "a", "b")
    expect(at(page, "b").locator(".written")).to_have_css("color", GREY)
    # Karo draws its letters itself, and they turn grey too. It gives the grey on as well.
    paint(page, "a", "k")
    expect(at(page, "k").locator("svg.ruling text").first).to_have_attribute("fill", "#aaaaaa")
    paint(page, "k", "c")
    expect(at(page, "c").locator(".written")).to_have_css("color", GREY)
    now = held(page, client)
    assert now["b"] == {**RULING, "text": "du", "trace": True}
    assert now["k"] == {**karo, "trace": True}
    assert now["c"] == {**RULING, "kind": "l1", "text": "wir", "trace": True}


def test_no_nachspuren_takes_nachspuren_off(editor):
    client = user()
    traced = {**RULING, "text": "du", "trace": True}
    page = editor(
        box("a", "ruling", {**RULING, "text": "ich"}),
        box("b", "ruling", traced, z=2),
        client=client,
    )
    undo = page.get_by_label("Rückgängig")
    paint(page, "a", "b")
    expect(at(page, "b").locator(".written")).not_to_have_css("color", GREY)
    assert held(page, client)["b"] == {**RULING, "text": "du"}
    undo.click()
    # One step is all there is.
    expect(undo).to_be_disabled()
    expect(at(page, "b").locator(".written")).to_have_css("color", GREY)
    assert held(page, client)["b"] == traced


def test_a_table_gives_a_lineatur_the_colour_of_its_lines(editor):
    client = user()
    # The table's text is blue and its lines are red: the lines of the Lineatur take the red.
    table = {**TABLE, "color": "#0000ff", "line": "#ff0000"}
    page = editor(
        box("tabelle", "table", table, h=30),
        box("b", "ruling", {**RULING, "color": "#888888", "trace": True}, z=3),
        client=client,
    )
    paint(page, "tabelle", "b")
    expect(at(page, "b").locator("svg.ruling")).to_have_attribute("stroke", "#ff0000")
    # A table has trace text too (#76): the brush takes the Lineatur's trace off it.
    assert held(page, client)["b"] == {**RULING, "color": "#ff0000"}


def test_a_table_that_names_no_line_colour_leaves_a_lineatur_its_own(editor):
    client = user()
    # A table made outside the editor may have no `line`: the Lineatur's lines must not vanish.
    page = editor(
        box("tabelle", "table", TABLE, h=30, mark="1."),
        box("b", "ruling", {**RULING, "color": "#888888"}, z=3),
        client=client,
    )
    paint(page, "tabelle", "b")
    expect(at(page, "b").locator("svg.ruling")).to_have_attribute("stroke", "#888888")
    b = whole(page, client)["b"]
    assert (b["mark"], b["props"]) == ("1.", {**RULING, "color": "#888888"})


def test_a_lineatur_gives_a_table_the_colour_of_its_lines(editor):
    client = user()
    table = {**TABLE, "color": "#0000ff", "line": "#ff0000"}
    page = editor(
        box("a", "ruling", {**RULING, "color": "#888888", "trace": True}),
        box("tabelle", "table", table, z=2, h=30),
        client=client,
    )
    paint(page, "a", "tabelle")
    expect(at(page, "tabelle").locator(".table")).to_have_css("border-color", "rgb(136, 136, 136)")
    # The text of the table keeps its colour: the brush brought the colour of lines alone.
    expect(at(page, "tabelle").locator(".table")).to_have_css("color", "rgb(0, 0, 255)")
    # The table takes the Lineatur's trace too, as both have trace text (#76).
    assert held(page, client)["tabelle"] == {**table, "line": "#888888", "trace": True}


def test_a_table_gives_a_table_the_colour_of_its_lines(editor):
    client = user()
    page = editor(
        box("a", "table", {**TABLE, "color": "#0000ff", "line": "#ff0000"}, h=30),
        box("tabelle", "table", {**TABLE, "color": "#00ff00", "line": "#222222"}, z=3, h=30),
        client=client,
    )
    paint(page, "a", "tabelle")
    expect(at(page, "tabelle").locator(".table")).to_have_css("border-color", RED_LINE)
    # Text colour to text colour, line colour to line colour.
    assert held(page, client)["tabelle"] == {**TABLE, "color": "#0000ff", "line": "#ff0000"}


def test_a_table_and_a_lineatur_take_the_colour_of_lines_together(editor):
    client = user()
    group = {"group": ["g"]}
    table = {**TABLE, "color": "#0000ff", "line": "#222222"}
    page = editor(
        box("a", "ruling", {**RULING, "color": "#ff0000"}),
        box("tabelle", "table", table, z=2, h=20, **group),
        box("b", "ruling", RULING, z=3, **group),
        box("c", "table", table, z=4, h=20),
        box("d", "ruling", RULING, z=5),
        client=client,
    )
    paint(page, "a", "tabelle", "b")
    # A selection takes it as a group does.
    pick(page, "a")
    page.keyboard.press("Control+Shift+C")
    pick(page, "c", "d")
    page.keyboard.press("Control+Shift+V")
    for name in ("tabelle", "c"):
        expect(at(page, name).locator(".table")).to_have_css("border-color", RED_LINE)
        expect(at(page, name).locator(".table")).to_have_css("color", "rgb(0, 0, 255)")
    for name in ("b", "d"):
        expect(at(page, name).locator("svg.ruling")).to_have_attribute("stroke", "#ff0000")
    now = held(page, client)
    assert now["tabelle"] == now["c"] == {**table, "line": "#ff0000"}
    assert now["b"] == now["d"] == {**RULING, "color": "#ff0000"}
