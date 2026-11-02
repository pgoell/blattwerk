"""The Geobrett on the sheet: nails, a band the teacher edits, and the answer of a task.

The docstrings name what each test proves. The geometry is tested with the model.
"""

from playwright.sync_api import expect
from test_gaps import panel, step
from test_words import redo, undo
from ui import box, doc, pick, tool, user

EMPTY = {"cols": 5, "rows": 5, "bands": [], "task": "leer", "seed": 7}
TRIANGLE = {
    "cols": 5,
    "rows": 5,
    "task": "spiegel",
    "figure": 0,
    "axis": {"dir": "v", "at": 2},
    "bands": [{"nails": [[0, 1], [2, 2], [0, 3]], "color": "#c0392b", "fill": True}],
    "seed": 7,
}


def brett(name, props):
    """A Geobrett of 100 mm square."""
    return box(name, "geobrett", props, w=100, h=100)


def props_of(stored):
    """The props of the one Geobrett on the sheet."""
    [block] = [b for b in stored["pages"][0]["blocks"] if b["type"] == "geobrett"]
    return block


def field(page, label):
    return page.locator(".panel").get_by_label(label, exact=True)


def test_an_empty_board_draws_twenty_five_nails_and_no_band(editor):
    """An empty Geobrett draws one nail for each of its 5 by 5 places and no band."""
    page = editor(brett("g", EMPTY))
    expect(page.locator(".geobrett .nail")).to_have_count(25)
    expect(page.locator(".geobrett .band")).to_have_count(0)
    expect(page.locator(".geobrett .ask")).to_have_count(0)


def test_breite_stores_its_prop_and_undoes_and_redoes(editor):
    """Nägel breit stores the nails across; Ctrl+Z brings 5 back and Ctrl+Y the new count."""
    client = user()
    page = editor(brett("g", EMPTY), client=client)
    pick(page, "g")
    step(page, lambda: field(page, "Nägel breit").fill("6"))
    assert props_of(doc(page, client))["props"]["cols"] == 6
    expect(page.locator(".geobrett .nail")).to_have_count(30)
    undo(page)
    assert props_of(doc(page, client))["props"]["cols"] == 5
    redo(page)
    assert props_of(doc(page, client))["props"]["cols"] == 6


def test_spiegelbild_draws_the_figure_the_axis_and_the_question(editor):
    """Spiegelbild ergänzen stores the first figure and draws its band, its axis and the question."""
    client = user()
    page = editor(brett("g", EMPTY), client=client)
    pick(page, "g")
    step(page, lambda: field(page, "Aufgabe").select_option("spiegel"))
    stored = props_of(doc(page, client))["props"]
    assert stored["task"] == "spiegel"
    assert stored["bands"][0]["nails"] == [[0, 1], [2, 2], [0, 3]]
    expect(page.locator(".geobrett .band")).to_have_count(1)
    expect(page.locator(".geobrett .axis")).to_have_count(1)
    expect(page.locator(".geobrett .ask")).to_have_text("Ergänze das Spiegelbild.")
    expect(page.locator(".geobrett .answer")).to_have_count(0)


def test_the_key_draws_the_mirror_image(editor):
    """Lösungen zeigen draws the mirror image; the pupil's sheet does not."""
    page = editor(brett("g", TRIANGLE))
    pick(page, "g")
    expect(page.locator(".geobrett .answer")).to_have_count(0)
    tool(page, "Lösungen zeigen").click()
    expect(page.locator(".geobrett .band.answer")).to_have_count(1)
    expect(page.locator(".geobrett .ask")).to_contain_text("Ergänze das Spiegelbild.")


def test_drehen_turns_the_band(editor):
    """Drehen turns the band 90° clockwise about its centre and stores the new nails."""
    client = user()
    page = editor(brett("g", TRIANGLE), client=client)
    pick(page, "g")
    step(page, lambda: panel(page, "Drehen").click())
    assert props_of(doc(page, client))["props"]["bands"][0]["nails"] == [[2, 1], [1, 3], [0, 1]]


def test_an_arrow_moves_the_band_and_leaves_the_block(editor):
    """With the nails focused, ArrowRight moves the band one nail and the block stays."""
    client = user()
    page = editor(brett("g", TRIANGLE), client=client)
    pick(page, "g")
    before = props_of(doc(page, client))["x"]
    page.locator(".panel").get_by_label("Nägel", exact=True).focus()
    step(page, lambda: page.keyboard.press("ArrowRight"))
    stored = props_of(doc(page, client))
    assert stored["props"]["bands"][0]["nails"] == [[1, 1], [3, 2], [1, 3]]
    assert stored["x"] == before


def test_clicking_a_nail_extends_the_band(editor):
    """A click on a nail adds it to the end of the band."""
    client = user()
    props = {**EMPTY, "bands": [{"nails": [[0, 0], [1, 0]], "color": "#c0392b", "fill": False}]}
    page = editor(brett("g", props), client=client)
    pick(page, "g")
    step(page, lambda: panel(page, "Nagel 2 0").click())
    assert props_of(doc(page, client))["props"]["bands"][0]["nails"] == [[0, 0], [1, 0], [2, 0]]


def test_farbe_stores_the_colour(editor):
    """Bandfarbe Blau stores that band's colour."""
    client = user()
    props = {**EMPTY, "bands": [{"nails": [[0, 0], [1, 0]], "color": "#c0392b", "fill": False}]}
    page = editor(brett("g", props), client=client)
    pick(page, "g")
    step(page, lambda: field(page, "Bandfarbe").select_option("Blau"))
    assert props_of(doc(page, client))["props"]["bands"][0]["color"] == "#1f6feb"
