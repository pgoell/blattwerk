"""Ctrl+Z and Ctrl+Y reach the sheet from a panel's checkbox and number field (#607).

The keys are the sheet's in a select and on a slider already. A checkbox and a number field took
them for their own, so an untick of Minutenstriche could not be undone by the keyboard.
"""

import pytest
from playwright.sync_api import expect
from test_gaps import step
from test_selbstkontrolle import field, props_of
from test_selbstkontrolle_panel import linked
from ui import TEXT, at, box, doc, pick, user

UHR = {
    "numbers": "all",
    "minutes": True,
    "ring": False,
    "task": "read",
    "answer": "box",
    "format": "12",
    "region": "nach",
    "count": 4,
    "cols": 4,
    "step": 15,
    "fill": "free",
    "times": [210, 585, 720, 370],
    "seed": 3,
}


def uhr(**more):
    """A clock block of 180 by 110 mm, as a block of the page is."""
    return box("u", "uhr", UHR, w=180, h=110, **more)


def minutes_box(page):
    return field(page, "Minutenstriche")


def stored_u_of(page, client, name):
    return {b["id"]: b for b in doc(page, client)["pages"][0]["blocks"]}[name]


def stored_u(page, client):
    return stored_u_of(page, client, "u")


def ticks(page):
    """The tick lines the clocks draw: 60 a clock with the minute ticks, 12 without."""
    return at(page, "u").locator("g.ticks line").count()


def test_ctrl_z_from_a_focused_minutenstriche_undoes_the_untick(editor):
    """#607: after an untick by the mouse, Ctrl+Z ticks the box again and the minutes come back."""
    client = user()
    page = editor(uhr(), client=client)
    pick(page, "u")
    drawn = ticks(page)
    step(page, lambda: minutes_box(page).click())
    expect(minutes_box(page)).not_to_be_checked()
    assert ticks(page) < drawn
    step(page, lambda: page.keyboard.press("Control+z"))
    expect(minutes_box(page)).to_be_checked()
    assert ticks(page) == drawn
    assert stored_u(page, client)["props"]["minutes"] is True


def test_ctrl_z_from_a_selbstkontrolle_link_checkbox_undoes(editor):
    """#607: after a link is taken off by the mouse, Ctrl+Z links the block again."""
    client = user()
    page = editor(*linked(client), client=client)
    pick(page, "s")
    link = page.locator(".panel input[type=checkbox]").first
    step(page, lambda: link.click())
    expect(link).not_to_be_checked()
    step(page, lambda: page.keyboard.press("Control+z"))
    expect(link).to_be_checked()
    assert props_of(doc(page, client), "s")["links"] == ["m"]


@pytest.mark.parametrize("keys", ["Control+y", "Control+Shift+z"], ids=["ctrl-y", "ctrl-shift-z"])
def test_redo_from_a_focused_checkbox_brings_the_untick_back(editor, keys):
    """#607: after Ctrl+Z, Ctrl+Y and Ctrl+Shift+Z from the focused box untick it again."""
    client = user()
    page = editor(uhr(), client=client)
    pick(page, "u")
    step(page, lambda: minutes_box(page).click())
    step(page, lambda: page.keyboard.press("Control+z"))
    expect(minutes_box(page)).to_be_checked()
    step(page, lambda: page.keyboard.press(keys))
    expect(minutes_box(page)).not_to_be_checked()
    assert stored_u(page, client)["props"]["minutes"] is False


def test_ctrl_z_from_a_number_field_undoes_the_app_steps_and_shows_the_number(editor):
    """#607: after a typed 12 and an untick, two Ctrl+Z from the Uhren field undo both: the box is
    ticked again and the field shows 4. The browser's input undo knows only the typed 12."""
    client = user()
    page = editor(uhr(), client=client)
    pick(page, "u")
    count = field(page, "Uhren")
    step(page, lambda: count.fill("12"))
    expect(at(page, "u").locator("circle.face")).to_have_count(12)
    step(page, lambda: minutes_box(page).click())
    expect(minutes_box(page)).not_to_be_checked()
    count.click()
    step(page, lambda: page.keyboard.press("Control+z"))
    expect(minutes_box(page)).to_be_checked()
    step(page, lambda: page.keyboard.press("Control+z"))
    expect(count).to_have_value("4")
    expect(at(page, "u").locator("circle.face")).to_have_count(4)
    assert stored_u(page, client)["props"]["count"] == 4
    assert stored_u(page, client)["props"]["minutes"] is True


ZAHLENSTRAHL = {
    "start": 0,
    "end": 20,
    "minor": 1,
    "major": 5,
    "labels": "major",
    "size": 12,
    "cut": False,
    "tasks": "random",
    "boxes": 3,
    "arrows": 0,
    "jumps": False,
}


def test_ctrl_z_from_a_zahlenstrahl_number_field_shows_the_old_number(editor):
    """#607: Ctrl+Z in the Ende field takes a typed 15 back: the field and the store show 20."""
    client = user()
    page = editor(box("z", "zahlenstrahl", ZAHLENSTRAHL, w=180, h=40), client=client)
    pick(page, "z")
    end = field(page, "Ende")
    step(page, lambda: end.fill("15"))
    step(page, lambda: page.keyboard.press("Control+z"))
    expect(end).to_have_value("20")
    assert stored_u_of(page, client, "z")["props"]["end"] == 20


def test_ctrl_z_from_selbstkontrolle_schriftgroesse_shows_the_old_size(editor):
    """#607: Ctrl+Z in the Schriftgröße field takes the typed 18 back: the field shows 14 again."""
    client = user()
    page = editor(*linked(client), client=client)
    pick(page, "s")
    size = field(page, "Schriftgröße")
    step(page, lambda: size.fill("18"))
    step(page, lambda: page.keyboard.press("Control+z"))
    expect(size).to_have_value("14")
    assert props_of(doc(page, client), "s")["size"] == 14


def test_ctrl_z_and_ctrl_y_from_a_select_undo_and_redo(editor):
    """Already works: the Zahlen select takes the sheet's Ctrl+Z and Ctrl+Y."""
    client = user()
    page = editor(uhr(), client=client)
    pick(page, "u")
    numbers = field(page, "Zahlen")
    step(page, lambda: numbers.select_option("none"))
    step(page, lambda: page.keyboard.press("Control+z"))
    expect(numbers).to_have_value("all")
    step(page, lambda: page.keyboard.press("Control+y"))
    expect(numbers).to_have_value("none")


def test_ctrl_z_and_ctrl_y_from_a_slider_undo_and_redo(editor):
    """Already works: the Zeilenabstand slider takes the sheet's Ctrl+Z and Ctrl+Y."""
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    pick(page, "a")
    spacing = page.locator(".panel").get_by_label("Zeilenabstand", exact=True)
    step(page, lambda: spacing.fill("2"))
    step(page, lambda: page.keyboard.press("Control+z"))
    expect(spacing).to_have_value("1.3")
    step(page, lambda: page.keyboard.press("Control+y"))
    expect(spacing).to_have_value("2")


def test_space_on_a_focused_checkbox_still_toggles_it(editor):
    """#607: Space on the focused Minutenstriche box still toggles it, and the store follows."""
    client = user()
    page = editor(uhr(), client=client)
    pick(page, "u")
    step(page, lambda: minutes_box(page).click())
    expect(minutes_box(page)).not_to_be_checked()
    step(page, lambda: page.keyboard.press("Space"))
    expect(minutes_box(page)).to_be_checked()
    assert stored_u(page, client)["props"]["minutes"] is True


def test_arrow_up_in_the_number_field_still_steps_it(editor):
    """#607: ArrowUp in the Uhren field still counts up: 4 becomes 5, with a fifth face."""
    client = user()
    page = editor(uhr(), client=client)
    pick(page, "u")
    count = field(page, "Uhren")
    count.click()
    step(page, lambda: page.keyboard.press("ArrowUp"))
    expect(count).to_have_value("5")
    expect(at(page, "u").locator("circle.face")).to_have_count(5)


def test_ctrl_z_from_a_checkbox_walks_back_two_steps(editor):
    """Beyond: two Ctrl+Z from the focused box undo the untick, then the Uhren typed before it."""
    client = user()
    page = editor(uhr(), client=client)
    pick(page, "u")
    count = field(page, "Uhren")
    step(page, lambda: count.fill("12"))
    step(page, lambda: minutes_box(page).click())
    step(page, lambda: page.keyboard.press("Control+z"))
    expect(minutes_box(page)).to_be_checked()
    step(page, lambda: page.keyboard.press("Control+z"))
    expect(count).to_have_value("4")
    assert stored_u(page, client)["props"]["count"] == 4


def test_ctrl_z_from_a_checkbox_focused_without_a_click_undoes(editor):
    """Beyond: a box that got the focus by the keyboard, not a click, takes Ctrl+Z the same way."""
    client = user()
    page = editor(uhr(), client=client)
    pick(page, "u")
    step(page, lambda: minutes_box(page).click())
    expect(minutes_box(page)).not_to_be_checked()
    minutes_box(page).blur()
    minutes_box(page).focus()
    step(page, lambda: page.keyboard.press("Control+z"))
    expect(minutes_box(page)).to_be_checked()
    assert stored_u(page, client)["props"]["minutes"] is True


def test_ctrl_z_from_a_number_field_with_a_refused_number_shows_the_sheets_number(editor):
    """Review: 9 columns are refused (1 to 6). Ctrl+Z from the field undoes the untick before,
    and the field shows the 4 the sheet holds, not the 9."""
    client = user()
    page = editor(uhr(), client=client)
    pick(page, "u")
    step(page, lambda: minutes_box(page).click())
    cols = field(page, "Spalten")
    cols.click()
    page.keyboard.press("Control+a")
    page.keyboard.type("9")
    expect(cols).to_have_value("9")
    step(page, lambda: page.keyboard.press("Control+z"))
    expect(minutes_box(page)).to_be_checked()
    expect(cols).to_have_value("4")
    assert stored_u(page, client)["props"]["cols"] == 4


def test_ctrl_z_in_the_n_field_is_the_fields_own(editor):
    """Review: the n of "Jedes n-te Wort" stays in the panel. Ctrl+Z there takes the typed
    digit back and leaves the sheet's last step (a nudge) alone."""
    page = editor(box("a", "text", {**TEXT, "text": "eins zwei drei vier"}))
    pick(page, "a")
    page.keyboard.press("ArrowRight")
    moved = at(page, "a").bounding_box()["x"]
    n = page.get_by_label("n", exact=True)
    was = n.input_value()
    n.click()
    page.keyboard.press("End")
    page.keyboard.type("4")
    expect(n).to_have_value(was + "4")
    page.keyboard.press("Control+z")
    expect(n).to_have_value(was)
    page.wait_for_timeout(300)
    assert at(page, "a").bounding_box()["x"] == moved
