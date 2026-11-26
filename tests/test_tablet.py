"""#1187: the tablet held upright has a rail of named tool groups, and the Format panel comes up from below."""

import pytest
from playwright.sync_api import expect
from ui import RECT, TEXT, at, bar, box, centre, expect_lit, expect_picked, maths, user
from ui_touch import swipe

GROUPS = ["Mehrere", "Text", "Bild", "Schreiben", "Mathe", "Tabelle", "Formen", "Seiten"]
BLOCKS = ".block[data-id]"


def rail(page):
    return page.get_by_role("toolbar", name="Einfügen")


def group(page, name):
    return rail(page).get_by_role("button", name=name, exact=True)


def listed(page, name):
    """Opens a group's list and gives it."""
    group(page, name).tap()
    menu = page.locator("dialog.menu")
    expect(menu).to_be_visible()
    return menu


def panel(page):
    return page.locator("aside.panel")


def upright(editor, *blocks, **more):
    return editor(*(blocks or [box("a", "text", TEXT, y=20)]), touch=True, **more)


def test_the_rail_holds_each_group_with_its_name_and_no_dock(editor):
    page = upright(editor)
    expect(rail(page)).to_have_class("rail")
    expect(rail(page).get_by_role("button")).to_have_text(GROUPS)
    expect(page.locator(".dock")).to_have_count(0)
    # At the window's left, under the bar, and the sheet beside it.
    place, sheet = rail(page).bounding_box(), page.locator(".sheet").first.bounding_box()
    assert place["x"] == 0 and place["x"] + place["width"] <= sheet["x"]
    assert place["width"] <= 80
    assert place["y"] >= page.locator("header").bounding_box()["height"] - 1
    for name in GROUPS:
        button = group(page, name)
        # No icon stands alone: the name is drawn, and a finger has 44 px each way.
        expect(button.locator("span")).to_be_visible()
        size = button.bounding_box()
        assert size["width"] >= 44 and size["height"] >= 44, (name, size)


@pytest.mark.parametrize(
    ("name", "tools"),
    [
        ("Text", ["Text", "Überschrift"]),
        ("Bild", ["Bild", "Symbol"]),
        ("Schreiben", ["Lineatur", "Namenszeile", "Punkte", "Suchsel"]),
    ],
)
def test_a_group_of_several_tools_lists_them_and_a_tap_adds_one(editor, name, tools):
    page = upright(editor)
    menu = listed(page, name)
    expect(menu.get_by_role("menuitem")).to_have_text(tools)
    # Beside the rail, not over it.
    assert menu.bounding_box()["x"] >= group(page, name).bounding_box()["x"] + 44
    for item in menu.get_by_role("menuitem").all():
        assert item.bounding_box()["height"] >= 44
    menu.get_by_role("menuitem", name=tools[-1], exact=True).tap()
    expect(menu).to_have_count(0)
    expect(page.locator(BLOCKS)).to_have_count(2)


def test_tabelle_adds_a_table_at_once(editor):
    page = upright(editor)
    group(page, "Tabelle").tap()
    expect(page.locator(f"{BLOCKS} .table")).to_have_count(1)
    expect(page.locator("dialog.menu")).to_have_count(0)


def test_formen_lists_every_shape(editor):
    page = upright(editor)
    menu = listed(page, "Formen")
    names = menu.get_by_role("menuitem").all_inner_texts()
    assert len(names) >= 9 and {"Rechteck", "Stern", "Doppelpfeil"} <= {n.strip() for n in names}
    menu.get_by_role("menuitem", name="Stern", exact=True).tap()
    expect(page.locator(BLOCKS)).to_have_count(2)


def test_mathe_opens_the_library_with_rechnen_and_strecke_before_its_cards(editor):
    client = user()
    page = upright(editor, client=client)
    group(page, "Mathe").tap()
    library = page.locator("dialog.library")
    expect(library).to_be_visible()
    expect(library.locator(".lead button")).to_have_text(["Rechnen", "Strecke"])
    expect(library.get_by_label("Zahlenmauer", exact=True)).to_be_visible()
    library.get_by_label("Zahlenmauer", exact=True).tap()
    expect(library).to_have_count(0)
    expect(page.locator(BLOCKS)).to_have_count(2)

    group(page, "Mathe").tap()
    library.locator(".lead").get_by_role("button", name="Rechnen").tap()
    expect(library).to_have_count(0)
    expect(page.locator(BLOCKS)).to_have_count(3)
    # A search is for the cards: the two tools make room.
    group(page, "Mathe").tap()
    library.get_by_label("Block suchen").fill("uhr")
    expect(library.locator(".lead")).to_have_count(0)


def test_seiten_opens_and_shuts_the_drawer_of_pages(editor):
    page = upright(editor)
    group(page, "Seiten").tap()
    expect(page.locator("aside.left")).to_be_visible()
    expect_lit(bar(page, "left"), "true")
    expect(group(page, "Seiten")).to_have_attribute("aria-pressed", "true")
    # The drawer lies over the rail: the bar's button shuts it.
    bar(page, "left").tap()
    expect(page.locator("aside.left")).to_have_count(0)


def test_a_tap_on_a_block_brings_the_panel_up_from_below(editor):
    page = upright(editor, box("a", "text", TEXT, y=20), box("b", "shape", RECT, y=60))
    expect(panel(page)).to_have_count(0)
    at(page, "a").tap()
    expect_picked(page, "a")
    expect(panel(page)).to_be_visible()
    place, window = panel(page).bounding_box(), page.viewport_size
    # The window's whole width, at its foot, and the desk ends where it begins.
    assert place["x"] == 0 and place["width"] == window["width"]
    assert abs(place["y"] + place["height"] - window["height"]) <= 1
    desk = page.locator(".desk").bounding_box()
    assert abs(desk["y"] + desk["height"] - place["y"]) <= 1
    assert place["height"] >= 300

    # "Fertig" shuts it and keeps the block picked.
    done = panel(page).get_by_role("button", name="Fertig", exact=True)
    assert done.bounding_box()["height"] >= 44
    done.tap()
    expect(panel(page)).to_have_count(0)
    expect_picked(page, "a")
    # The next block picked brings it back, and a tap beside the blocks sends it away.
    at(page, "b").tap()
    expect(panel(page)).to_be_visible()
    page.locator(".sheet").first.tap(position={"x": 8, "y": 8})
    expect_picked(page)
    expect(panel(page)).to_have_count(0)


def test_the_panel_shows_the_three_tabs(editor):
    client = user()
    page = upright(editor, box("m", "maths", maths(client), y=20, h=60), client=client, tabs=True)
    at(page, "m").tap()
    tabs = panel(page).get_by_role("tablist", name="Einstellungen").get_by_role("tab")
    expect(tabs).to_have_text(["Aufgaben", "Aussehen", "Lage"])


def test_a_block_low_on_the_page_stays_in_view_above_the_panel(editor):
    page = upright(editor, box("a", "text", TEXT, y=20), box("low", "text", TEXT, y=230, h=20))
    low = at(page, "low")
    low.scroll_into_view_if_needed()
    low.tap()
    expect(panel(page)).to_be_visible()
    expect_picked(page, "low")
    # The desk has scrolled: the whole block lies between the bar and the panel.
    top = panel(page).bounding_box()["y"]
    page.wait_for_function(
        "(top) => document.querySelector('.block.sel').getBoundingClientRect().bottom <= top",
        arg=top,
    )
    place = low.bounding_box()
    assert place["y"] >= page.locator("header").bounding_box()["height"]


def test_a_swipe_down_by_the_grip_shuts_the_panel(editor):
    page = upright(editor)
    at(page, "a").tap()
    grip = panel(page).locator(".grab")
    expect(grip).to_be_visible()
    x, y = centre(grip.locator("i"))
    # Across is no swipe down: the panel stays.
    swipe(page, (x, y), (x + 120, y + 5))
    expect(panel(page)).to_be_visible()
    swipe(page, (x, y), (x + 4, y + 30), (x + 6, y + 90))
    expect(panel(page)).to_have_count(0)
    expect_picked(page, "a")


def test_the_bar_keeps_the_title_undo_redo_and_the_download(editor):
    page = upright(editor)
    top = page.locator("header .top")
    expect(top.get_by_label("Titel", exact=True)).to_be_visible()
    for name in ("Rückgängig", "Wiederholen", "Herunterladen"):
        expect(top.get_by_label(name, exact=True)).to_be_visible()


def test_on_its_side_the_tablet_keeps_the_computers_layout(editor):
    page = editor(box("a", "text", TEXT, y=20), touch="landscape")
    expect(page.locator(".rail")).to_have_count(0)
    expect(page.locator(".insert[role=toolbar]")).to_be_visible()
    # The Format panel stands at the right as on the computer, with no grip.
    expect(panel(page)).to_be_visible()
    expect(panel(page).locator(".grab")).to_be_hidden()
    assert panel(page).bounding_box()["x"] > page.viewport_size["width"] / 2
