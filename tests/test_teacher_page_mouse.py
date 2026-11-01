"""The teacher-page tool's mouse: click, drag, key-drag, wheel, middle-drag and the edge swipe."""
# The fixtures imported below are named again as a test's arguments.
# ruff: noqa: F811

import pytest
from playwright.sync_api import expect
from test_bar import TIP
from test_teacher_page import (
    ONE,
    TWO,
    desk_at,
    folder,  # noqa: F401
    middle,
    pytestmark,  # noqa: F401
    scrolled,
    shape,
    size,
    slider,
    tool,
    xy,
)
from test_zoom import (
    expect_scroll,
    fit,
    roomy,
    scroll,
)
from ui import (
    TABLE,
    at,
    bar,
    box,
    centre,
    expect_picked,
    saved,
    user,
)

# The mouse


def test_click_on_a_blocks_words_picks_it_and_shows_the_window(editor, folder):
    page = editor(box("a", "text", ONE), box("b", "text", TWO, z=2))
    said = tool.click(page, "Zwei")
    expect_picked(page, "b")
    assert said == f"clicked at {middle(at(page, 'b').get_by_text('Zwei'))}: {folder / 'last.png'}"
    assert size(folder / "last.png") == (1400, 1000)


def test_shift_click_adds_a_second_block_to_the_first(editor):
    page = editor(box("a", "text", ONE), box("b", "text", TWO, z=2))
    tool.click(page, "Eins")
    expect_picked(page, "a")
    tool.shift_click(page, "Zwei")
    expect_picked(page, "a", "b")


def test_double_click_at_a_table_cell_opens_it_and_type_writes_there(editor):
    page = editor(box("t", "table", TABLE))
    tool.double_click(page, xy(at(page, "t").get_by_text("Z", exact=True)))
    cell = at(page, "t").locator("textarea")
    expect(cell).to_be_focused()
    expect(cell).to_have_value("Z")
    tool.type_(page, "9")
    expect(cell).to_have_value("Z9")


def test_hover_on_an_icon_by_its_name_shows_that_name(editor):
    page = editor(box("a", "text", ONE))
    button = page.get_by_label("Format und Ansicht", exact=True)
    assert button.evaluate(TIP) is None
    said = tool.hover(page, "Format und Ansicht")
    assert said.startswith(f"mouse at {middle(button)}: ")
    assert button.evaluate(TIP)["content"] == '"Format und Ansicht"'


def test_406_1_click_takes_the_button_when_a_heading_shares_its_name(editor):
    # With a text picked, the left panel's button and the right panel's heading are both "Text".
    page = editor(box("a", "text", ONE))
    tool.click(page, "Eins")
    expect_picked(page, "a")
    button = page.get_by_label("Text", exact=True)
    said = tool.click(page, "Text")
    assert said.startswith(f"clicked at {middle(button)}: ")
    # The button adds a text, and the new one is picked.
    expect(page.locator(".block")).to_have_count(2)
    expect(at(page, "a")).not_to_have_class("block sel")


def test_drag_moves_a_block_and_undo_takes_it_back(editor):
    page = editor(box("a", "text", ONE))
    was = at(page, "a").bounding_box()
    x, y = centre(at(page, "a"))
    tool.drag(page, "Eins", f"{x + 100:g},{y + 150:g}")
    expect_picked(page, "a")
    now = at(page, "a").bounding_box()
    # The block may snap to the sheet, by less than it was moved.
    assert abs(now["x"] - was["x"] - 100) < 40 and abs(now["y"] - was["y"] - 150) < 40, now
    tool.key(page, "Control+z")
    expect(page.get_by_label("Rückgängig", exact=True)).to_be_disabled()
    assert at(page, "a").bounding_box() == was


def test_drag_along_the_slider_moves_it(editor):
    client = user()
    page = shape(editor, client)
    on = slider(page).bounding_box()
    y = on["y"] + on["height"] / 2
    tool.drag(page, f"{on['x'] + 10:g},{y:g}", f"{on['x'] + on['width'] - 2:g},{y:g}")
    expect(slider(page)).to_have_value("3")
    assert saved(page, client)[0]["props"]["strokeWidth"] == 3


def test_wheel_scrolls_the_desk_down_and_up(editor):
    page = editor(box("a", "text", ONE), pages=[{"blocks": []}])
    assert scrolled(page) == 0
    tool.wheel(page, xy(page.locator(".desk")), "300")
    page.wait_for_function("document.querySelector('.desk').scrollTop === 300")
    tool.wheel(page, xy(page.locator(".desk")), "-200")
    page.wait_for_function("document.querySelector('.desk').scrollTop === 100")
    with pytest.raises(tool.Refused, match='"down" is not a number'):
        tool.wheel(page, "5,5", "down")


def test_key_drag_with_space_held_pans_the_desk(editor):
    # Issue #581: no verb held a key during a drag, so the run tapped Space.
    page = editor(box("a", "text", ONE))
    roomy(page)
    left, top = scroll(page)
    said = tool.key_drag(page, "Space", desk_at(page), desk_at(page, 110, 70))
    assert said.startswith("dragged with Space held from "), said
    expect_scroll(page, left - 100, top - 60)
    expect(page.locator(".block.sel")).to_have_count(0)
    expect(page.locator(".hand")).to_have_count(0)


def test_key_drag_refuses_two_names_that_are_never_in_the_window_together(editor, monkeypatch):
    page = editor(box("a", "text", ONE))

    def point(page, target):
        tool.NOTES.append("turned the page to it")
        return 300.0, 300.0

    monkeypatch.setattr(tool, "point", point)
    with pytest.raises(tool.Refused, match="not in the window together"):
        tool.key_drag(page, "Space", "FROM", "TO")
    tool.NOTES.clear()


def test_middle_drag_pans_the_desk(editor):
    page = editor(box("a", "text", ONE))
    roomy(page)
    left, top = scroll(page)
    tool.middle_drag(page, desk_at(page), desk_at(page, 110, 70))
    expect_scroll(page, left - 100, top - 60)
    expect(page.locator(".block.sel")).to_have_count(0)


def test_middle_drag_at_the_fitted_zoom_moves_nothing_and_picks_nothing(editor):
    page = editor(box("a", "text", ONE))
    fit(page).click()
    left, top = scroll(page)
    tool.middle_drag(page, desk_at(page), desk_at(page, 70, 50))
    expect_scroll(page, left, top)
    expect(page.locator(".block.sel")).to_have_count(0)


def test_middle_drag_refuses_two_names_that_are_never_in_the_window_together(editor, monkeypatch):
    page = editor(box("a", "text", ONE))

    def point(page, target):
        tool.NOTES.append("turned the page to it")
        return 300.0, 300.0

    monkeypatch.setattr(tool, "point", point)
    with pytest.raises(tool.Refused, match="not in the window together"):
        tool.middle_drag(page, "FROM", "TO")
    tool.NOTES.clear()


def test_swipe_in_from_the_right_edge_opens_the_format_drawer_in_the_upright_window(editor):
    page = editor(box("a", "text", ONE))
    tool.resize(page, "820", "1180")
    expect(bar(page, "right")).to_have_attribute("aria-pressed", "false")
    tool.swipe(page, "817,600", "660,600")
    expect(bar(page, "right")).to_have_attribute("aria-pressed", "true")


def test_swipe_refuses_two_names_that_are_never_in_the_window_together(editor, monkeypatch):
    page = editor(box("a", "text", ONE))

    def point(page, target):
        tool.NOTES.append("turned the page to it")
        return 300.0, 300.0

    monkeypatch.setattr(tool, "point", point)
    with pytest.raises(tool.Refused, match="not in the window together"):
        tool.swipe(page, "FROM", "TO")
    tool.NOTES.clear()
