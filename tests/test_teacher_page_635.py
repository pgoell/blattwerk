"""The teacher-page faults from issue #635 that the fourteenth run hit."""

import pytest
from playwright.sync_api import expect
from test_teacher_page import pytestmark, tool  # noqa: F401
from ui import FIELD, TEXT, box, maths, pick, user


def test_635_a_scrolled_zahlenraum_is_turned_back_into_the_window(editor):
    # The panel had been scrolled, and click Zahlenraum said the list lay outside it.
    client = user()
    page = editor(box("a", "maths", maths(client)), client=client)
    pick(page, "a")
    select = page.locator(".panel").get_by_label("Zahlenraum", exact=True)
    select.evaluate(
        """el => {
            const panel = el.closest(".panel");
            panel.scrollTop = panel.scrollHeight;
        }"""
    )
    assert select.bounding_box()["y"] < 0
    said = tool.click(page, "Zahlenraum")
    assert said.endswith("(turned the page to it)"), said
    expect(select).to_be_focused()


def test_635_value_uebertrag_reads_the_lit_button(editor):
    # Übertrag is a row of buttons. value looked for a field and found none.
    client = user()
    page = editor(box("a", "maths", maths(client)), client=client)
    pick(page, "a")
    assert tool.value(page, "Übertrag") == "Übertrag is Egal"
    tool.click(page, "Mit")
    assert tool.value(page, "Übertrag") == "Übertrag is Mit"
    with pytest.raises(tool.Refused, match='no field on the page is called "Nein"'):
        tool.value(page, "Nein")


def test_635_click_klassenarbeit_takes_the_button_and_turns_the_panel(editor):
    # Three matches lay outside the window: the button, and the word in two little pages.
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    page.get_by_role("tab", name="Vorlagen").click()
    button = page.get_by_role("button", name="Klassenarbeit", exact=True)
    expect(button).to_be_visible()
    page.locator("aside.left").evaluate("el => { el.scrollTop = 0 }")
    assert button.bounding_box()["y"] >= page.evaluate("innerHeight")
    lines = tool.where(page, "Klassenarbeit").splitlines()
    assert len(lines) >= 3
    assert all("(outside the window)" in line for line in lines), lines
    said = tool.click(page, "Klassenarbeit")
    assert "(turned the page to it)" in said, said
    expect(page.get_by_text("/ 60 Punkte").first).to_be_visible()


def test_635_click_ganze_seite_in_the_open_list_fits_the_page(editor):
    # where prints the bar's button and the list's item. The click takes the list's.
    page = editor(box("a", "text", TEXT))
    zoom = page.locator("button.zoom").first
    before = zoom.inner_text()
    zoom.click()
    expect(page.locator("dialog.menu").get_by_role("menuitem", name="Ganze Seite")).to_be_visible()
    tool.click(page, "Ganze Seite")
    expect(page.locator("dialog.menu")).to_have_count(0)
    expect(zoom).not_to_have_text(before)


def test_635_a_folded_zoom_is_read_after_mehr(editor):
    page = editor(box("a", "text", TEXT))
    for wide, high in (("820", "1180"), ("1000", "800")):
        tool.resize(page, wide, high)
        with pytest.raises(tool.Refused, match='it may lie under "Mehr"'):
            tool.where(page, "%")
    tool.click(page, "Mehr")
    tool.click(page, "Zoom")
    expect(page.locator("dialog.menu")).to_be_visible()
    assert tool.value(page, "Zoom in Prozent").startswith("Zoom in Prozent is ")


def test_635_plus_is_the_german_key_and_control_plus_zooms(editor):
    page = editor(box("a", "text", {**TEXT, "text": ""}))
    page.evaluate(
        """() => {
            window.lastKey = null;
            addEventListener("keydown", (e) => {
                if (e.key === "+") window.lastKey = {key: e.key, code: e.code, ctrl: e.ctrlKey};
            }, true);
        }"""
    )
    zoom = page.locator("button.zoom").first
    before = zoom.inner_text()
    tool.key(page, "Control++")
    expect(zoom).not_to_have_text(before)
    assert page.evaluate("() => window.lastKey") == {
        "key": "+",
        "code": "BracketRight",
        "ctrl": True,
    }
    pick(page, "a")
    page.keyboard.press("Enter")
    page.keyboard.press("Control+a")
    tool.key(page, "+")
    expect(page.locator(FIELD)).to_have_text("+")
    assert page.evaluate("() => window.lastKey.code") == "BracketRight"
