"""The words in the bar stand at the middle of their button."""

import pytest
from ui import TEXT, box, expect

WIDE = {"width": 1600, "height": 900}


@pytest.mark.parametrize("name", ["Lösungen zeigen", "Herunterladen"])
def test_the_words_of_a_bar_button_stand_at_its_middle(editor, name):
    """The panel's box of syllable words has the class `words` too, and its margin pushed these up."""
    page = editor(box("a", "text", TEXT))
    page.set_viewport_size(WIDE)
    words = page.locator(".top .words").filter(has_text=name)
    expect(words).to_be_visible()
    off = words.evaluate(
        """(el) => {
            const mid = (r) => (r.top + r.bottom) / 2;
            const own = el.closest("button, label");
            const icon = own.querySelector("svg");
            return [mid(el.getBoundingClientRect()) - mid(own.getBoundingClientRect()),
                    mid(el.getBoundingClientRect()) - mid(icon.getBoundingClientRect()),
                    getComputedStyle(el).marginBottom];
        }"""
    )
    assert abs(off[0]) <= 1 and abs(off[1]) <= 1, off


def test_the_shapes_start_where_the_icons_of_the_other_tools_start(editor):
    """The shapes had no inset of their own, and stood 4 px nearer the window's edge than the rows above."""
    page = editor(box("a", "text", TEXT))
    lefts = page.locator(".insert").evaluate(
        """(el) => {
            const left = (q) => Math.round(el.querySelector(q).getBoundingClientRect().left);
            return [left('[aria-label="Text"] svg'), left('.shapes svg'), left('[aria-label="Weitere Formen"] svg')];
        }"""
    )
    assert len(set(lefts)) == 1, lefts


def test_the_left_panel_leads_to_the_lernwoerter(editor):
    """Under "Deutsch" at the left, the tool opens the sheet's list at the right, and shuts it again."""
    page = editor(box("a", "text", TEXT))
    tool = page.locator(".insert").get_by_role("button", name="Lernwörter", exact=True)
    expect(page.locator('.insert .sep[data-name="Deutsch"]')).to_be_visible()
    tool.click()
    expect(
        page.locator(".panel").get_by_role("textbox", name="Lernwörter", exact=True)
    ).to_be_visible()
    expect(tool).to_have_attribute("aria-pressed", "true")
    tool.click()
    expect(
        page.locator(".panel").get_by_role("textbox", name="Lernwörter", exact=True)
    ).to_be_hidden()
    expect(tool).to_have_attribute("aria-pressed", "false")


def test_a_narrow_window_keeps_its_tab_and_has_no_tool_for_the_lernwoerter(editor):
    page = editor(box("a", "text", TEXT))
    page.set_viewport_size({"width": 1000, "height": 900})
    expect(
        page.locator(".dock, .insert").get_by_role("button", name="Lernwörter", exact=True)
    ).to_have_count(0)
    expect(page.get_by_role("tab", name="Lernwörter")).to_be_visible()
