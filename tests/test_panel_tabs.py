"""The three tabs of the format panel (#1181): Aufgaben, Aussehen and Lage.

Each block opens on the tab a teacher came for, a tab with nothing in it is not offered, the
panel keeps the tab of each kind of block until the page is loaded again, and the arrow keys
walk the tabs.
"""

from playwright.sync_api import expect
from ui import RECT, TEXT, at, box, maths, pick, user


def tabs(page):
    return page.get_by_role("tablist", name="Einstellungen").get_by_role("tab")


def tab(page, name):
    return page.get_by_role("tablist", name="Einstellungen").get_by_role("tab", name=name)


def field(page, label):
    return page.locator(".panel").get_by_label(label, exact=True)


def sheet(editor):
    client = user()
    blocks = (
        box("m", "maths", maths(client)),
        box("t", "text", TEXT, y=120),
        box("s", "shape", RECT, y=180),
    )
    return editor(*blocks, client=client, tabs=True)


def test_a_maths_block_opens_on_aufgaben(editor):
    page = sheet(editor)
    pick(page, "m")
    expect(tabs(page)).to_have_text(["Aufgaben", "Aussehen", "Lage"])
    expect(tab(page, "Aufgaben")).to_have_attribute("aria-selected", "true")
    expect(page.locator(".panel").get_by_role("heading", name="Rechenart")).to_be_visible()
    expect(field(page, "X")).to_be_hidden()
    expect(field(page, "Schrift größer")).to_be_hidden()


def test_a_tab_shows_its_settings_and_hides_the_others(editor):
    page = sheet(editor)
    pick(page, "m")
    tab(page, "Lage").click()
    expect(tab(page, "Lage")).to_have_attribute("aria-selected", "true")
    expect(field(page, "X")).to_be_visible()
    expect(page.locator(".panel").get_by_role("heading", name="Rechenart")).to_be_hidden()
    tab(page, "Aussehen").click()
    expect(field(page, "Schrift größer")).to_be_visible()
    expect(field(page, "X")).to_be_hidden()


def test_a_text_opens_on_aussehen(editor):
    page = sheet(editor)
    pick(page, "t")
    expect(tab(page, "Aussehen")).to_have_attribute("aria-selected", "true")
    expect(field(page, "Schriftart")).to_be_visible()
    expect(page.locator(".panel").get_by_role("switch", name="Lücke", exact=True)).to_be_hidden()
    tab(page, "Aufgaben").click()
    expect(page.locator(".panel").get_by_role("switch", name="Lücke", exact=True)).to_be_visible()


def test_a_shape_has_no_empty_tab(editor):
    page = sheet(editor)
    pick(page, "s")
    expect(tab(page, "Aussehen")).to_have_attribute("aria-selected", "true")
    for name in tabs(page).all_text_contents():
        tab(page, name).click()
        shown = page.locator(".panel .pane > :not(.pane)").filter(visible=True)
        expect(shown.first).to_be_visible()


def test_the_panel_keeps_the_tab_of_each_kind_of_block(editor):
    page = sheet(editor)
    pick(page, "m")
    tab(page, "Lage").click()
    pick(page, "t")
    expect(tab(page, "Aussehen")).to_have_attribute("aria-selected", "true")
    pick(page, "m")
    expect(tab(page, "Lage")).to_have_attribute("aria-selected", "true")
    expect(field(page, "X")).to_be_visible()


def test_the_arrow_keys_walk_the_tabs_and_leave_the_block_where_it_is(editor):
    page = sheet(editor)
    pick(page, "m")
    before = at(page, "m").bounding_box()
    tab(page, "Aufgaben").focus()
    page.keyboard.press("ArrowRight")
    expect(tab(page, "Aussehen")).to_have_attribute("aria-selected", "true")
    expect(tab(page, "Aussehen")).to_be_focused()
    page.keyboard.press("End")
    expect(tab(page, "Lage")).to_be_focused()
    page.keyboard.press("ArrowRight")
    expect(tab(page, "Aufgaben")).to_be_focused()
    page.keyboard.press("ArrowLeft")
    expect(tab(page, "Lage")).to_have_attribute("aria-selected", "true")
    assert at(page, "m").bounding_box() == before
