"""Lines of a table: its style and width, the border buttons on picked cells, and Schneidelinien.

Each test names the box of #80 it holds (A1 to I8). The lines are read from the doc.
"""

import pytest
from playwright.sync_api import expect
from ui import at, box, doc, pick, user

CELLS = [["a", "b", "c"], ["d", "e", "f"], ["g", "h", "i"]]
GRID = {"cells": CELLS, "cols": [1, 1, 1], "size": 14, "align": "center", "line": "#222222"}
FOUR = ("lineStyle", "lineWidth", "cut", "edges")


def cell(page, n):
    return at(page, "t").locator(f'.table > div[data-cell="{n}"]')


def props(page, client):
    return next(b for b in doc(page, client)["pages"][0]["blocks"] if b["id"] == "t")["props"]


def drawn(p):
    """The lines that hold an entry, as `h<row>,<col>` or `v<row>,<col>`."""
    edges = p.get("edges", {"h": [], "v": []})
    lines = set()
    for axis in ("h", "v"):
        for r, row in enumerate(edges[axis]):
            lines |= {f"{axis}{r},{c}" for c, e in enumerate(row) if e}
    return lines


def open_cell(page, n):
    """Picks the table, then opens its cell n."""
    pick(page, "t")
    cell(page, n).dblclick()
    expect(cell(page, n).locator("textarea")).to_be_focused()


def square(page):
    """Opens the top left cell and picks the 2 by 2 square with a Shift+click on the centre cell."""
    open_cell(page, 0)
    cell(page, 4).click(modifiers=["Shift"])
    expect(page.locator(".table > div.picked")).to_have_count(4)


def style(page):
    return page.get_by_label("Linienart")


def border(page, label):
    return page.get_by_role("group", name="Rahmen").get_by_role("button", name=label, exact=True)


def schneidelinien(page):
    return page.get_by_role("button", name="Schneidelinien", exact=True)


def test_a1_a2_style_goes_to_the_whole_table(editor):
    """A1, A2: with the table picked and no cell open, the style goes to every line."""
    client = user()
    page = editor(box("t", "table", GRID), client=client)
    pick(page, "t")
    style(page).select_option("dashed")
    expect(style(page)).to_have_value("dashed")
    assert props(page, client)["lineStyle"] == "dashed"
    assert "edges" not in props(page, client)


@pytest.mark.parametrize(
    ("label", "lines"),
    [
        ("Oben", {"h0,0", "h0,1"}),
        ("Unten", {"h2,0", "h2,1"}),
        ("Links", {"v0,0", "v1,0"}),
        ("Rechts", {"v0,2", "v1,2"}),
        ("Innen waagerecht", {"h1,0", "h1,1"}),
        ("Innen senkrecht", {"v0,1", "v1,1"}),
        ("Außen", {"h0,0", "h0,1", "h2,0", "h2,1", "v0,0", "v1,0", "v0,2", "v1,2"}),
        ("Innen", {"h1,0", "h1,1", "v0,1", "v1,1"}),
        (
            "Alle",
            {"h0,0", "h0,1", "h1,0", "h1,1", "h2,0", "h2,1"}
            | {"v0,0", "v0,1", "v0,2", "v1,0", "v1,1", "v1,2"},
        ),
    ],
)
def test_a3_border_buttons_write_their_lines_only(editor, label, lines):
    """A3: each border button puts the pen on its own lines of the picked 2 by 2 square."""
    client = user()
    page = editor(box("t", "table", GRID), client=client)
    square(page)
    style(page).select_option("dotted")
    border(page, label).click()
    expect(page.locator(".table > div.picked")).to_have_count(4)
    p = props(page, client)
    assert drawn(p) == lines
    for name in lines:
        axis, (r, c) = name[0], map(int, name[1:].split(","))
        assert p["edges"][axis][r][c] == {"style": "dotted", "width": 0.25}


def test_a_style_keeps_the_width_and_a_width_keeps_the_style(editor):
    """A1, A4: the style and the width of a table are set one after the other and both hold."""
    client = user()
    page = editor(box("t", "table", GRID), client=client)
    pick(page, "t")
    style(page).select_option("dashed")
    slider = page.get_by_label("Linienstärke")
    slider.focus()
    page.keyboard.press("ArrowRight")
    expect(page.locator("output", has_text="0,50 mm")).to_be_visible()
    now = props(page, client)
    assert (now["lineStyle"], now["lineWidth"]) == ("dashed", 0.5)
    style(page).select_option("dotted")
    expect(style(page)).to_have_value("dotted")
    now = props(page, client)
    assert (now["lineStyle"], now["lineWidth"]) == ("dotted", 0.5)


def test_a9_solid_asked_of_a_plain_table_writes_no_key(editor):
    """A9: Durchgezogen chosen on a table that has no key leaves it an old table."""
    client = user()
    page = editor(box("t", "table", GRID), client=client)
    pick(page, "t")
    before = props(page, client)
    style(page).select_option("dashed")
    expect(page.locator(".table.edged")).to_have_count(1)
    page.keyboard.press("Control+z")
    expect(page.locator(".table.edged")).to_have_count(0)
    style(page).select_option("solid")
    assert props(page, client) == before
    expect(page.locator(".table.edged")).to_have_count(0)


def test_a4_slider_sets_the_width_in_steps(editor):
    """A4: the slider Linienstärke goes from 0,25 to 3 mm in steps; the table gets the width."""
    client = user()
    page = editor(box("t", "table", GRID), client=client)
    pick(page, "t")
    slider = page.get_by_label("Linienstärke")
    expect(slider).to_have_attribute("min", "0.25")
    expect(slider).to_have_attribute("max", "3")
    expect(slider).to_have_attribute("step", "0.25")
    slider.focus()
    page.keyboard.press("ArrowRight")
    page.keyboard.press("ArrowRight")
    expect(page.locator("output", has_text="0,75 mm")).to_be_visible()
    assert props(page, client)["lineWidth"] == 0.75


def test_a5_schneidelinien_on_and_off(editor):
    """A5: one click makes the lines dashed and thin, with scissors; a second click, plain."""
    client = user()
    page = editor(box("t", "table", GRID), client=client)
    pick(page, "t")
    schneidelinien(page).click()
    expect(schneidelinien(page)).to_have_attribute("aria-pressed", "true")
    p = props(page, client)
    assert p["cut"] is True and p["lineStyle"] == "dashed" and p["lineWidth"] == 0.25
    assert "edges" not in p
    schneidelinien(page).click()
    expect(schneidelinien(page)).to_have_attribute("aria-pressed", "false")
    p = props(page, client)
    assert not any(key in p for key in FOUR)


def test_a9_old_table_loads_solid_and_a_text_change_adds_no_keys(editor):
    """A9: a table with none of the four keys is solid; a text change adds none."""
    client = user()
    page = editor(box("t", "table", GRID), client=client)
    pick(page, "t")
    expect(style(page)).to_have_value("solid")
    open_cell(page, 4)
    page.keyboard.type("x")
    expect(cell(page, 4)).to_contain_text("x")
    assert not any(key in props(page, client) for key in FOUR)


def test_a10_each_change_is_one_undo_step_and_redo_brings_it_back(editor):
    """A10: style, a border button and Schneidelinien each undo and redo once."""
    client = user()
    page = editor(box("t", "table", GRID), client=client)
    pick(page, "t")
    style(page).select_option("dashed")
    expect(style(page)).to_have_value("dashed")
    doc(page, client)
    page.keyboard.press("Control+z")
    expect(style(page)).to_have_value("solid")
    page.keyboard.press("Control+y")
    expect(style(page)).to_have_value("dashed")
    schneidelinien(page).click()
    expect(schneidelinien(page)).to_have_attribute("aria-pressed", "true")
    doc(page, client)
    page.keyboard.press("Control+z")
    expect(schneidelinien(page)).to_have_attribute("aria-pressed", "false")
    page.keyboard.press("Control+y")
    expect(schneidelinien(page)).to_have_attribute("aria-pressed", "true")


def test_i1_a_line_between_two_cells_is_one_line_and_the_later_click_wins(editor):
    """I1: the right border of a cell is the left border of its neighbour; the later click wins."""
    client = user()
    page = editor(box("t", "table", GRID), client=client)
    open_cell(page, 0)
    style(page).select_option("dashed")
    border(page, "Rechts").click()
    style(page).select_option("dotted")
    cell(page, 1).dblclick()
    expect(cell(page, 1).locator("textarea")).to_be_focused()
    border(page, "Links").click()
    p = props(page, client)
    assert drawn(p) == {"v0,1"}
    assert p["edges"]["v"][0][1] == {"style": "dotted", "width": 0.25}


def test_i2_cells_stay_picked_after_a_border_button(editor):
    """I2: after a border button the cells stay picked and the table stays open."""
    client = user()
    page = editor(box("t", "table", GRID), client=client)
    square(page)
    border(page, "Alle").click()
    expect(page.locator(".table > div.picked")).to_have_count(4)
    expect(page.locator(".table textarea")).to_have_count(1)


def test_i3_inner_buttons_are_disabled_on_one_cell_and_one_row(editor):
    """I3: one cell open turns the inner buttons off; one picked row, Innen and Innen waagerecht."""
    client = user()
    page = editor(box("t", "table", GRID), client=client)
    open_cell(page, 0)
    for label in ("Innen", "Innen waagerecht", "Innen senkrecht"):
        expect(border(page, label)).to_be_disabled()
    expect(border(page, "Alle")).to_be_enabled()
    cell(page, 2).click(modifiers=["Shift"])
    expect(page.locator(".table > div.picked")).to_have_count(3)
    expect(border(page, "Innen waagerecht")).to_be_disabled()
    expect(border(page, "Innen")).to_be_disabled()
    expect(border(page, "Innen senkrecht")).to_be_enabled()


def test_extra_a_table_with_broken_edges_takes_a_border(editor):
    """Beyond the brief: a table with broken `edges` still takes a border button."""
    client = user()
    broken = {**GRID, "lineStyle": "dotted", "edges": {"h": [[None]], "v": []}}
    page = editor(box("t", "table", broken), client=client)
    open_cell(page, 0)
    style(page).select_option("dashed")
    border(page, "Oben").click()
    p = props(page, client)
    assert drawn(p) == {"h0,0"}
    assert p["lineStyle"] == "dotted"


def test_extra_a_one_cell_table_has_no_inner_lines(editor):
    """Beyond the brief: a 1 by 1 table has its four rim lines and no inner ones."""
    client = user()
    single = {**GRID, "cells": [["a"]], "cols": [1]}
    page = editor(box("t", "table", single), client=client)
    open_cell(page, 0)
    expect(border(page, "Innen")).to_be_disabled()
    style(page).select_option("dashed")
    border(page, "Außen").click()
    p = props(page, client)
    assert drawn(p) == {"h0,0", "h1,0", "v0,0", "v0,1"}


def test_a10_a_drag_of_the_slider_is_one_undo_step(editor):
    """A10: three steps of the slider are one step of undo, and one redo brings the last back."""
    client = user()
    page = editor(box("t", "table", GRID), client=client)
    pick(page, "t")
    slider = page.get_by_label("Linienstärke")
    slider.focus()
    for _ in range(3):
        page.keyboard.press("ArrowRight")
    expect(page.locator("output", has_text="1,00 mm")).to_be_visible()
    assert props(page, client)["lineWidth"] == 1
    page.keyboard.press("Control+z")
    expect(page.locator("output", has_text="0,25 mm")).to_be_visible()
    assert "lineWidth" not in props(page, client)
    page.keyboard.press("Control+y")
    expect(page.locator("output", has_text="1,00 mm")).to_be_visible()
    assert props(page, client)["lineWidth"] == 1


def test_a3_whole_table_border_with_no_cell_open(editor):
    """A3: with the table picked and no cell open, a border button gives its lines the table's own
    style back; on a table that has it already it changes nothing and adds no step of undo."""
    client = user()
    dotted = {"style": "dotted", "width": 1}
    h = [[None] * 3, [dotted] * 3, [dotted] * 3, [None] * 3]
    v = [[None, dotted, None, None], [None] * 4, [None] * 4]
    look = {"lineStyle": "dashed", "edges": {"h": h, "v": v}}
    page = editor(box("t", "table", {**GRID, **look}), box("p", "table", GRID, z=4), client=client)
    pick(page, "t")
    border(page, "Innen waagerecht").click()
    expect(page.get_by_label("Rückgängig", exact=True)).to_be_enabled()
    assert drawn(props(page, client)) == {"v0,1"}
    border(page, "Innen senkrecht").click()
    p = props(page, client)
    assert "edges" not in p and p["lineStyle"] == "dashed"
    # A plain table: every border is as the table draws it anyway.
    page.keyboard.press("Control+z")
    page.keyboard.press("Control+z")
    expect(page.get_by_label("Rückgängig", exact=True)).to_be_disabled()
    pick(page, "p")
    for label in ("Alle", "Außen", "Oben"):
        border(page, label).click()
    expect(page.get_by_label("Rückgängig", exact=True)).to_be_disabled()
    expect(page.locator(".table.edged")).to_have_count(1)


def test_a10_a_border_button_is_one_undo_step(editor):
    """A10: a border button undoes in one step and redo brings its lines back."""
    client = user()
    page = editor(box("t", "table", GRID), client=client)
    square(page)
    style(page).select_option("dashed")
    border(page, "Außen").click()
    expect(page.locator('.table line[data-style="dashed"]')).not_to_have_count(0)
    lines = drawn(props(page, client))
    assert len(lines) == 8
    page.keyboard.press("Escape")
    page.keyboard.press("Control+z")
    expect(page.locator(".table.edged")).to_have_count(0)
    assert "edges" not in props(page, client)
    page.keyboard.press("Control+y")
    expect(page.locator(".table.edged")).to_have_count(1)
    assert drawn(props(page, client)) == lines


def test_a_locked_table_shows_no_border_buttons(editor):
    """I3: the border buttons stand only where they can draw: not for a locked table, and not
    for a table picked with another block."""
    page = editor(box("t", "table", GRID, locked=True), box("u", "table", GRID, z=4))
    pick(page, "u")
    expect(page.get_by_role("group", name="Rahmen")).to_be_visible()
    pick(page, "t")
    expect(style(page)).to_be_visible()
    expect(page.get_by_role("group", name="Rahmen")).to_have_count(0)
    pick(page, "t", "u")
    expect(page.get_by_role("group", name="Rahmen")).to_have_count(0)
