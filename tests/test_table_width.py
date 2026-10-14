"""A new column grows its table by the average width, up to the page's right margin (#602).

The table keeps its place on the page: its right edge stays at the margin of 15 mm from the right
edge of an A4 page (195 mm), and the columns narrow instead. A table already past it keeps its
width. Removing a column is as before.
"""

import pytest
from test_gaps import panel, step
from ui import at, box, pick, saved, user

ROW = {"cells": [["a", "b", "c"]], "cols": [1, 1, 1], "size": 14, "align": "center"}
PAIR = {"cells": [["a", "b"]], "cols": [1, 1], "size": 14, "align": "center"}


def table(name, props, w, x=15):
    """A table of w mm at x mm from the left, one row high."""
    return box(name, "table", props, w=w, x=x)


def stored(page, client):
    """The table as the server holds it."""
    return {b["id"]: b for b in saved(page, client)}["t"]


def test_a_new_column_keeps_a_default_table_inside_the_margin(editor):
    """#602: "Eine Spalte mehr" on a 180 mm table at x 15 keeps it 180 mm wide, 4 columns."""
    client = user()
    page = editor(table("t", ROW, 180), client=client)
    pick(page, "t")
    step(page, lambda: panel(page, "Eine Spalte mehr").click())
    got = stored(page, client)
    assert got["w"] == 180
    assert len(got["props"]["cols"]) == 4
    assert got["x"] + got["w"] <= 195


@pytest.mark.parametrize("button, cell", [("Spalte rechts", 2), ("Spalte links", 0)])
def test_a_column_from_the_cell_keeps_the_table_inside_the_margin(editor, button, cell):
    """#602: "Spalte rechts" and "Spalte links" on a 180 mm table keep it 180 mm wide."""
    client = user()
    page = editor(table("t", ROW, 180), client=client)
    pick(page, "t")
    at(page, "t").locator(".table > div[data-cell]").nth(cell).dblclick()
    step(page, lambda: page.get_by_role("button", name=button, exact=True).click())
    got = stored(page, client)
    assert got["w"] == 180
    assert len(got["props"]["cols"]) == 4
    assert got["x"] + got["w"] <= 195


def test_a_narrow_table_still_widens_by_its_average_column(editor):
    """#602: a 60 mm table of 2 columns grows by their average, 30 mm, to 90 mm."""
    client = user()
    page = editor(table("t", PAIR, 60), client=client)
    pick(page, "t")
    step(page, lambda: panel(page, "Eine Spalte mehr").click())
    assert stored(page, client)["w"] == pytest.approx(90, abs=0.2)


def test_a_table_grows_only_to_the_margin(editor):
    """#602: a 170 mm table at x 15 has 10 mm to the margin, so a new column takes it to 180 mm."""
    client = user()
    page = editor(table("t", ROW, 170), client=client)
    pick(page, "t")
    step(page, lambda: panel(page, "Eine Spalte mehr").click())
    assert stored(page, client)["w"] == 180


def test_one_undo_gives_back_the_width_and_the_columns(editor):
    """#602: one undo after a new column gives back the 180 mm and the 3 columns."""
    client = user()
    page = editor(table("t", ROW, 180), client=client)
    pick(page, "t")
    step(page, lambda: panel(page, "Eine Spalte mehr").click())
    step(page, lambda: page.get_by_label("Rückgängig", exact=True).first.click())
    got = stored(page, client)
    assert got["w"] == 180
    assert len(got["props"]["cols"]) == 3


def test_a_table_already_past_the_margin_does_not_grow(editor):
    """#602, beyond the brief: a 190 mm table at x 15 is past the margin, so it keeps its width."""
    client = user()
    page = editor(table("t", ROW, 190), client=client)
    pick(page, "t")
    step(page, lambda: panel(page, "Eine Spalte mehr").click())
    got = stored(page, client)
    assert got["w"] == 190
    assert len(got["props"]["cols"]) == 4
