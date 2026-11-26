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
    """Under "Deutsch" at the left, the tool puts writing lines on the sheet, picked, and the
    sheet's list stands in their panel at the right."""
    page = editor(box("a", "text", TEXT))
    tool = page.locator(".insert").get_by_role("button", name="Lernwörter", exact=True)
    expect(page.locator('.insert .sep[data-name="Deutsch"]')).to_be_visible()
    tool.click()
    expect(page.locator(".block.sel")).to_have_count(1)
    expect(
        page.locator(".panel").get_by_role("textbox", name="Lernwörter", exact=True)
    ).to_be_visible()
    expect(tool).not_to_have_attribute("aria-pressed", "true")


def test_a_narrow_window_has_the_tool_for_the_lernwoerter_and_no_tab_for_them(editor):
    page = editor(box("a", "text", TEXT))
    page.set_viewport_size({"width": 1000, "height": 900})
    expect(
        page.locator(".dock").get_by_role("button", name="Lernwörter", exact=True)
    ).to_be_visible()
    expect(page.get_by_role("tab", name="Format")).to_be_visible()
    expect(page.get_by_role("tab", name="Lernwörter")).to_have_count(0)
