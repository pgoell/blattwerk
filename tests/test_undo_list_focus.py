"""Ctrl+Z and Ctrl+Y on a list of the panel that has the focus are the sheet's, as in PowerPoint."""

import pytest
from playwright.sync_api import expect
from ui import RULING, TABLE, TEXT, box, pick

LISTS = [
    ("text", TEXT, "Schriftart"),
    ("ruling", RULING, "Art der Lineatur"),
    ("ruling", RULING, "Schriftart auf den Zeilen"),
    ("table", TABLE, "Schriftart der Tabelle"),
]


@pytest.mark.parametrize(("kind", "props", "label"), LISTS, ids=[label for *_, label in LISTS])
def test_ctrl_z_on_a_list_that_has_the_focus_takes_the_pick_back(editor, kind, props, label):
    page = editor(box("a", kind, props))
    pick(page, "a")
    choice = page.get_by_label(label, exact=True)
    start = choice.input_value()
    choice.focus()
    page.keyboard.press("ArrowDown")
    expect(choice).not_to_have_value(start)
    picked = choice.input_value()
    expect(choice).to_be_focused()
    page.keyboard.press("Control+z")
    expect(choice).to_have_value(start)
    expect(page.get_by_label("Rückgängig", exact=True)).to_be_disabled()
    page.keyboard.press("Control+y")
    expect(choice).to_have_value(picked)
