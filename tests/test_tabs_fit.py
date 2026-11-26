"""#1189: at 1280 x 800 each tab of the Format panel shows all it holds, with nothing to scroll.

What is set for few sheets lies folded under its heading, one click away.
"""

import re

import pytest
from playwright.sync_api import expect
from test_cells import cell
from test_menu import props
from ui import RECT, TABLE, TEXT, box, maths, pick, user

KINDS = ["text", "shape", "line", "image", "symbol", "table", "ruling", "maths", "name", "points"]
CARDS = [
    "Zahlenmauer", "Zahlenhaus", "Zahlenkette", "Rechendreieck", "Rechenrad", "Rechentabelle",
    "Pfeilbild", "Operatorfeld", "Malquadrat", "Halbschriftlich rechnen", "Textaufgaben", "Formel",
    "Zehnerfeld", "Hunderterfeld", "Zahlenstrahl", "Stellenwert-Bild", "Stellenwerttafel",
    "Zahlzerlegung", "Zerlegungsfeld", "Uhr", "Geobrett", "Karofeld", "Diagramm",
    "Magisches Quadrat", "Selbstkontrolle", "Lösungsfeld",
]  # fmt: skip
SMALL = {"width": 1280, "height": 800}


def panel(page):
    return page.locator("aside.panel")


def overflow(page):
    """How many px of each tab lie below the panel's foot, by the tab's name."""
    over = {}
    tabs = panel(page).get_by_role("tablist", name="Einstellungen").get_by_role("tab")
    expect(tabs.first).to_be_visible()
    for tab in tabs.all():
        tab.click()
        expect(tab).to_have_attribute("aria-selected", "true")
        over[tab.inner_text()] = panel(page).evaluate("el => el.scrollHeight - el.clientHeight")
    return over


@pytest.mark.parametrize("theme", [None, ""], ids=["blattform", "plain"])
@pytest.mark.parametrize("kind", KINDS)
def test_each_tab_of_a_block_fits_the_small_window(editor, kind, theme):
    client = user()
    block = box("a", "shape" if kind == "line" else kind, props(client, kind), w=80, h=40)
    page = editor(block, client=client, tabs=True, theme=theme)
    page.set_viewport_size(SMALL)
    pick(page, "a")
    over = overflow(page)
    assert not any(over.values()), over


@pytest.mark.parametrize("card", CARDS)
def test_each_tab_of_a_maths_block_fits_the_small_window(editor, card):
    page = editor(tabs=True)
    page.set_viewport_size(SMALL)
    page.locator(".dock, .insert").get_by_label(re.compile("^Mathe(-Blöcke)?$")).click()
    page.locator("dialog.library").get_by_label(card, exact=True).click()
    over = overflow(page)
    assert not any(over.values()), over


def test_the_library_holds_no_card_this_file_does_not_name(editor):
    page = editor(tabs=True)
    page.locator(".dock, .insert").get_by_label(re.compile("^Mathe(-Blöcke)?$")).click()
    cards = page.locator("dialog.library button[aria-label]").evaluate_all(
        "els => els.map((el) => el.getAttribute('aria-label'))"
    )
    assert set(CARDS) <= set(cards)
    assert not [name for name in cards if name not in CARDS and not name.startswith("Schließen")]


SUMS = {
    "bis 1000": {"max": 1000},
    "geteilt": {"ops": ["/"], "max": 100},
    "Lücke": {"format": "gap"},
    "schriftlich": {"format": "written", "max": 1000},
    "vergleichen": {"format": "compare", "max": 100},
    "drei Zahlen": {"numbers": 3},
}


@pytest.mark.parametrize("sums", SUMS)
def test_rechnen_fits_in_each_format(editor, sums):
    client = user()
    page = editor(
        box("a", "maths", maths(client, **SUMS[sums]), w=120, h=40), client=client, tabs=True
    )
    page.set_viewport_size(SMALL)
    pick(page, "a")
    over = overflow(page)
    assert not any(over.values()), over


@pytest.mark.parametrize("state", ["cell picked", "cell open"])
def test_a_table_with_a_cell_fits(editor, state):
    client = user()
    page = editor(box("t", "table", TABLE, w=120, h=40), client=client, tabs=True)
    page.set_viewport_size(SMALL)
    pick(page, "t")
    cell(page, "t", 0).click()
    if state == "cell open":
        cell(page, "t", 0).dblclick()
    over = overflow(page)
    assert not any(over.values()), over


def test_two_blocks_fit(editor):
    page = editor(box("a", "text", TEXT, y=20), box("b", "shape", RECT, y=80), tabs=True)
    page.set_viewport_size(SMALL)
    pick(page, "a")
    page.keyboard.press("Control+a")
    over = overflow(page)
    assert not any(over.values()), over


def fold(page, title):
    return panel(page).get_by_role("button", name=title, exact=True)


def test_a_fold_opens_shuts_and_is_remembered_for_the_next_block(editor):
    page = editor(box("a", "text", TEXT, y=20), box("b", "text", TEXT, y=80), tabs=True)
    pick(page, "a")
    panel(page).get_by_role("tab", name="Lage").click()
    layers = fold(page, "Ebene")
    expect(layers).to_have_attribute("aria-expanded", "false")
    expect(panel(page).get_by_role("button", name="Nach vorn", exact=True)).to_have_count(0)
    # The keyboard opens it, as any button.
    layers.focus()
    page.keyboard.press("Enter")
    expect(layers).to_have_attribute("aria-expanded", "true")
    expect(panel(page).get_by_role("button", name="Nach vorn", exact=True)).to_be_visible()
    # Open for the next block too, until she shuts it.
    pick(page, "b")
    expect(fold(page, "Ebene")).to_have_attribute("aria-expanded", "true")
    fold(page, "Ebene").click()
    expect(fold(page, "Ebene")).to_have_attribute("aria-expanded", "false")
    expect(panel(page).get_by_role("button", name="Nach vorn", exact=True)).to_have_count(0)


def test_a_text_shows_its_script_and_a_shape_its_fill(editor):
    page = editor(box("a", "text", TEXT, y=20), box("b", "shape", RECT, y=80), tabs=True)
    pick(page, "a")
    panel(page).get_by_role("tab", name="Aussehen").click()
    expect(fold(page, "Schrift")).to_have_attribute("aria-expanded", "true")
    expect(fold(page, "Füllung und Rand")).to_have_attribute("aria-expanded", "false")
    pick(page, "b")
    panel(page).get_by_role("tab", name="Aussehen").click()
    expect(fold(page, "Schrift")).to_have_attribute("aria-expanded", "false")
    expect(fold(page, "Füllung und Rand")).to_have_attribute("aria-expanded", "true")


def test_rechnen_keeps_its_first_settings_in_view_and_folds_the_rest(editor):
    client = user()
    page = editor(box("a", "maths", maths(client), w=120, h=40), client=client, tabs=True)
    pick(page, "a")
    for heading in ("Rechenart", "Zahlenraum", "Zehnerübergang", "Format", "Anzahl"):
        expect(panel(page).get_by_role("heading", name=heading, exact=True)).to_be_visible()
    more = fold(page, "Weitere Einstellungen")
    expect(more).to_have_attribute("aria-expanded", "false")
    expect(panel(page).get_by_role("switch", name="Aufgaben mit 0")).to_have_count(0)
    more.click()
    expect(panel(page).get_by_role("switch", name="Aufgaben mit 0")).to_be_visible()
    expect(panel(page).get_by_role("heading", name="Aufgabenfamilien", exact=True)).to_be_visible()


def test_a_task_field_drawn_as_a_grid_stays_in_its_own_tab(editor):
    """The fields of a Zehnerfeld's numbers lie in a grid of their own style: they showed in every tab."""
    page = editor(tabs=True)
    page.locator(".dock, .insert").get_by_label(re.compile("^Mathe(-Blöcke)?$")).click()
    page.locator("dialog.library").get_by_label("Zehnerfeld", exact=True).click()
    expect(panel(page).get_by_label("Erste Zahl", exact=True)).to_be_visible()
    panel(page).get_by_role("tab", name="Lage").click()
    expect(panel(page).get_by_label("X", exact=True)).to_be_visible()
    expect(panel(page).get_by_label("Erste Zahl", exact=True)).to_be_hidden()
