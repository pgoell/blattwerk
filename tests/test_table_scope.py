"""The table's panel says what a setting changes (#1188): the whole table or the picked cells."""

from playwright.sync_api import expect
from test_cells import GRID, cell, open_cell
from ui import box, pick, user


def heading(page, name):
    return page.locator(".panel").get_by_role("heading", name=name, exact=True)


def tab(page, name):
    return page.get_by_role("tablist", name="Einstellungen").get_by_role("tab", name=name)


def test_with_no_cell_open_the_panel_shows_only_the_table_settings(editor):
    client = user()
    page = editor(box("t", "table", GRID), client=client, tabs=True)
    pick(page, "t")
    expect(tab(page, "Aufgaben")).to_have_attribute("aria-selected", "true")
    expect(heading(page, "Ganze Tabelle").filter(visible=True)).to_have_count(1)
    tab(page, "Aussehen").click()
    expect(heading(page, "Ganze Tabelle").filter(visible=True)).to_have_count(1)
    expect(page.locator(".panel h2", has_text="Ausgewählte Zellen")).to_have_count(0)
    expect(page.locator(".panel").get_by_label("Schriftart der Zellen")).to_have_count(0)
    expect(page.locator(".panel .cap").filter(visible=True)).to_have_text(["Schriftart"])


def test_with_cells_picked_their_settings_stand_under_their_own_heading(editor):
    client = user()
    page = editor(box("t", "table", GRID), client=client, tabs=True)
    open_cell(page, "t", 0)
    expect(heading(page, "Ausgewählte Zellen (1)").filter(visible=True)).to_have_count(1)
    cell(page, "t", 4).click(modifiers=["Shift"])
    expect(heading(page, "Ausgewählte Zellen (4)").filter(visible=True)).to_have_count(1)
    tab(page, "Aussehen").click()
    shown = page.locator(".panel h2").filter(visible=True)
    expect(shown).to_have_text(["Ganze Tabelle", "Ausgewählte Zellen (4)", "Nummerierung"])
    # Each font list has its name over it, and the size and the marks belong to the cells.
    expect(page.locator(".panel .cap").filter(visible=True)).to_have_text(["Schriftart"] * 2)
    cells = heading(page, "Ausgewählte Zellen (4)")
    size = page.locator(".panel").get_by_label("Schrift größer", exact=True)
    assert size.bounding_box()["y"] > cells.bounding_box()["y"]
    table_font = page.locator(".panel").get_by_label("Schriftart der Tabelle", exact=True)
    assert table_font.bounding_box()["y"] < cells.bounding_box()["y"]
