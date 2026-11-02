"""A Diagramm on the sheet: columns, bars and a pie, and a bar the pupil draws.

The docstrings name what each test proves. The geometry is tested with the model.
"""

from playwright.sync_api import expect
from test_gaps import panel, step
from ui import box, doc, pick, tool, user

RED = "#c0392b"
BLUE = "#1f6feb"


def point(value, label, color, answer=None):
    """One data point. `answer` is set only when the pupil's value is empty."""
    item = {"value": value, "label": label, "color": color}
    if answer is not None:
        item["answer"] = answer
    return item


def chart(name, props):
    """A Diagramm of 150 by 90 mm."""
    return box(name, "diagramm", props, w=150, h=90)


def field(page, label):
    return page.locator(".panel").get_by_label(label, exact=True)


def stored(page, client):
    """The props of the one Diagramm on the sheet."""
    blocks = [b for b in doc(page, client)["pages"][0]["blocks"] if b["type"] == "diagramm"]
    return blocks[0]["props"]


COLUMNS = {
    "kind": "saeulen",
    "points": [point("3,5 kg", "Äpfel", RED), point("6", "Birnen", BLUE)],
    "legend": True,
    "values": "aussen",
    "axes": "beide",
    "xTitle": "Obst",
    "yTitle": "Menge",
    "grid": "haupt",
    "seed": 7,
}


def test_columns_draw_the_bars_the_unit_the_legend_and_the_axes(editor):
    """Säulen draw one bar per value, the unit, both titles, the legend and the main grid."""
    page = editor(chart("d", COLUMNS))
    root = page.locator(".diagramm")
    expect(root).to_have_attribute("data-kind", "saeulen")
    expect(root.locator(".balken")).to_have_count(2)
    expect(root.locator(".value").first).to_have_text("3,5 kg")
    expect(root.locator(".legend")).to_have_count(2)
    expect(root.locator(".axis")).to_have_count(2)
    expect(root.locator(".title")).to_have_text(["Obst", "Menge"])
    expect(root.locator(".grid.haupt")).not_to_have_count(0)
    expect(root.locator(".grid.zwischen")).to_have_count(0)
    expect(root.locator(".slice")).to_have_count(0)


def test_an_empty_value_is_drawn_only_in_the_key(editor):
    """A point with no value draws no bar; Lösungen zeigen draws it from the answer."""
    props = {
        **COLUMNS,
        "points": [point("", "Äpfel", RED, "3,5 kg"), point("6", "Birnen", BLUE)],
    }
    page = editor(chart("d", props))
    root = page.locator(".diagramm")
    expect(root.locator(".balken")).to_have_count(1)
    expect(root.locator(".balken.answer")).to_have_count(0)
    pick(page, "d")
    tool(page, "Lösungen zeigen").click()
    expect(root.locator(".balken")).to_have_count(2)
    expect(root.locator(".balken.answer")).to_have_count(1)
    expect(root.locator(".value.answer")).to_have_text("3,5 kg")


def test_bars_draw_and_the_fine_grid_follows_the_props(editor):
    """Balken draw sideways, and Haupt- und Zwischenschritte draw the fine grid."""
    props = {**COLUMNS, "kind": "balken", "grid": "zwischen", "axes": "x", "values": "innen"}
    page = editor(chart("d", props))
    root = page.locator(".diagramm")
    expect(root).to_have_attribute("data-kind", "balken")
    expect(root.locator(".balken")).to_have_count(2)
    expect(root.locator(".grid.zwischen")).not_to_have_count(0)
    expect(root.locator(".axis")).to_have_count(1)
    expect(root.locator(".axis")).to_have_attribute("data-dir", "x")
    expect(root.locator(".value").first).to_have_attribute("data-place", "innen")


def test_the_panel_stores_the_kind_the_legend_and_a_new_point(editor):
    """Art, Legende, Punkt dazu and Punkt löschen store the chart the sheet draws."""
    client = user()
    page = editor(chart("d", COLUMNS), client=client)
    pick(page, "d")
    step(page, lambda: field(page, "Art").select_option("kreis"))
    expect(page.locator(".diagramm .slice")).to_have_count(2)
    step(page, lambda: field(page, "Legende").uncheck())
    expect(page.locator(".diagramm .legend")).to_have_count(0)
    step(page, lambda: panel(page, "Punkt dazu").click())
    assert len(stored(page, client)["points"]) == 3
    assert stored(page, client)["kind"] == "kreis"
    assert stored(page, client)["legend"] is False
    step(page, lambda: panel(page, "Punkt löschen").click())
    props = stored(page, client)
    assert props["kind"] == "kreis"
    assert [p["label"] for p in props["points"]] == ["Äpfel", "Birnen"]


def test_clearing_the_value_hides_the_bar_until_the_key(editor):
    """Clearing Wert and writing Lösung stores the gap; the key draws that bar."""
    client = user()
    props = {**COLUMNS, "points": [point("4", "Äpfel", RED)], "legend": False}
    page = editor(chart("d", props), client=client)
    pick(page, "d")
    step(page, lambda: field(page, "Wert").fill(""))
    step(page, lambda: field(page, "Lösung").fill("4"))
    expect(page.locator(".diagramm .balken")).to_have_count(0)
    got = stored(page, client)["points"][0]
    assert got["value"] == ""
    assert got["answer"] == "4"
    tool(page, "Lösungen zeigen").click()
    expect(page.locator(".diagramm .balken.answer")).to_have_count(1)


def test_axes_grid_and_value_place_follow_the_panel(editor):
    """Achsen, Hilfslinien and Werte store what the chart draws."""
    client = user()
    page = editor(chart("d", COLUMNS), client=client)
    pick(page, "d")
    step(page, lambda: field(page, "Achsen").select_option("keine"))
    step(page, lambda: field(page, "Hilfslinien").select_option("zwischen"))
    step(page, lambda: field(page, "Werte").select_option("innen"))
    root = page.locator(".diagramm")
    expect(root.locator(".axis")).to_have_count(0)
    expect(root.locator(".title")).to_have_count(0)
    expect(root.locator(".grid.zwischen")).not_to_have_count(0)
    expect(root.locator(".value").first).to_have_attribute("data-place", "innen")
    props = stored(page, client)
    assert props["axes"] == "keine"
    assert props["grid"] == "zwischen"
    assert props["values"] == "innen"
