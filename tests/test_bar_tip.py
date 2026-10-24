"""The name under a bar button, on hover and in a narrow window.

The bar helpers live in test_bar.py."""

import pytest
from test_bar import (
    HELD,
    THEMES,
    TIP,
    expect_fitted,
    sized,
    text,
)


@THEMES
def test_a_bar_buttons_name_shows_whole_under_it_on_hover(editor, theme):
    """A5"""
    page = sized(editor, text("a"), width=900, height=1200, touch=False, theme=theme)
    expect_fitted(page)
    for name in ("Seiten und Vorlagen", "Einfügen", "Format und Ansicht", "Mehr"):
        button = page.locator("header .top").get_by_label(name, exact=True)
        button.hover()
        tip = button.evaluate(TIP)
        assert tip and tip["content"] == f'"{name}"', tip
        assert tip["cut"] is None, tip
        assert tip["box"]["left"] >= 0 and tip["box"]["right"] <= tip["window"][0], tip
        assert tip["box"]["top"] >= 0 and tip["box"]["bottom"] <= tip["window"][1], tip


@THEMES
@pytest.mark.parametrize("width", [360, 600])
def test_a_bar_buttons_name_stays_in_a_narrow_window_and_under_its_button_where_it_has_room(
    editor, theme, width
):
    """A2, I5, I7 (#284)"""
    page = sized(editor, text("a"), width=width, height=900, touch=False, theme=theme)
    buttons = page.locator("header .top .ib:visible").all()
    assert len(buttons) > 10
    shifted = []
    for button in buttons:
        button.hover()
        tip = button.evaluate(TIP)
        name = button.get_attribute("aria-label")
        assert tip and tip["content"] == f'"{name}"', (name, tip)
        assert tip["cut"] is None, (name, tip)
        assert tip["box"]["left"] >= 0 and tip["box"]["right"] <= width, (name, tip["box"])
        assert tip["box"]["top"] >= 0 and tip["box"]["bottom"] <= tip["window"][1], (name, tip)
        on = button.bounding_box()
        middle = on["x"] + on["width"] / 2
        half = (tip["box"]["right"] - tip["box"]["left"]) / 2
        # Centred where that leaves it clear of the window's edges, else as near to it as it gets.
        want = min(max(middle, 4 + half), width - 4 - half)
        assert abs(tip["box"]["left"] + half - want) < 0.5, (name, tip["box"])
        assert not page.evaluate(HELD)["scrolls"], name
        if want != middle:
            shifted.append(name)
    # The button at the end of the first row is one that has no room; it is off, as most are here.
    assert {360: "Wiederholen", 600: "Gruppieren"}[width] in shifted, shifted
    assert len(shifted) < len(buttons) / 2, shifted


@THEMES
def test_for_a_finger_no_name_shows_in_a_narrow_window_and_nothing_shifts(editor, theme):
    """I8 (#284)"""
    page = sized(editor, text("a"), width=360, height=900, touch=True, theme=theme)
    buttons = page.locator("header .top .ib:visible, .stage .dock .ib:visible").all()
    assert len(buttons) > 10
    for button in buttons:
        button.hover()
        assert button.evaluate(TIP) is None, button.get_attribute("aria-label")
        assert set(page.evaluate(HELD)["shifts"]) <= {"", "0px"}, button.get_attribute("aria-label")
