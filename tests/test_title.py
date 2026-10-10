"""The bar shows as much of a sheet's title as it has room for (#318).

A title that is cut ends in three dots, shows whole under the pointer, and whole while it is
edited: the bar then folds more of its commands under "Mehr".
"""

import json

import pytest
from playwright.sync_api import expect
from test_bar import BAR, expect_fitted, more, sized, text

WIDTHS = pytest.mark.parametrize("width", [1280, 820, 360])
ENDS = pytest.mark.parametrize("end", ["Enter", "Escape", "click"])
# One that has room at any of the widths, one that a row of 360 px holds, one that no bar holds
# with its commands in it, and one of 80 wide letters, which no bar holds at all.
SHORT = "TR3 Bild"
ROW = "Rechnen bis 100 mit Zehnerübergang"
LONG = "Die Geschichte vom kleinen Igel, der eines Nachts nicht schlafen wollte"
TOO = "Mm" * 40
# What the title's field says of itself, and whether the window scrolls sideways.
TITLE = """() => {
    const el = document.querySelector("header input[aria-label=Titel]");
    return {
        whole: el.scrollWidth <= el.clientWidth,
        dots: getComputedStyle(el).textOverflow === "ellipsis",
        focused: document.activeElement === el,
        tip: el.title,
        width: el.offsetWidth,
        scrolls: document.documentElement.scrollWidth > innerWidth,
    };
}"""


def titled(editor, width, title, theme=None):
    """The editor at that width with the title typed in, and the field, which has the focus."""
    page = sized(editor, text("a"), width=width, height=1024, touch=False, theme=theme)
    field = page.get_by_label("Titel")
    field.fill(title)
    expect(field).to_be_focused()
    return page, field


def leave(page, end):
    if end == "click":
        page.locator(".desk").click(position={"x": 4, "y": 4})
    else:
        page.keyboard.press(end)
    expect(page.get_by_label("Titel")).not_to_be_focused()


def expect_title(page, width, **want):
    """Waits until the title's field is as wanted, in a bar that fits, and gives what it says."""
    want["scrolls"] = False
    fitted = f"(want) => Object.keys(want).every((key) => ({TITLE})()[key] === want[key])"
    page.wait_for_function(fitted, arg=want, timeout=2000)
    # Above a phone's width the bar is one row.
    expect_fitted(page, row=width > 700)
    return page.evaluate(TITLE)


@WIDTHS
def test_a_title_that_has_room_shows_whole(editor, width):
    """A14, A15"""
    for title in ("TR4 Zwei Seiten", "TR3 Bild und Tabelle") if width > 700 else (SHORT,):
        page, _ = titled(editor, width, title)
        leave(page, "Enter")
        expect_title(page, width, whole=True, focused=False, tip=title)


@WIDTHS
def test_a_title_the_bar_has_no_room_for_ends_in_three_dots(editor, width):
    """A14, A15"""
    page, _ = titled(editor, width, LONG)
    leave(page, "Enter")
    got = expect_title(page, width, whole=False, dots=True, focused=False, tip=LONG)
    if width > 700:
        # As much as the bar has room for: the most a title may take, or all that folds is folded.
        names = page.evaluate(BAR)["names"]
        assert abs(got["width"] - 0.34 * width) <= 1 or not names, json.dumps([got, names])


@WIDTHS
@ENDS
def test_a_title_shows_whole_while_it_is_edited_and_is_cut_again_after(editor, width, end):
    """A16, I8"""
    page, field = titled(editor, width, SHORT)
    leave(page, "Enter")
    short = expect_title(page, width, whole=True, focused=False)
    before = page.evaluate(BAR)["names"]
    field.fill(ROW)
    wide = expect_title(page, width, whole=True, focused=True)
    assert wide["width"] > short["width"]
    during = page.evaluate(BAR)["names"]
    if width > 700:
        # What lost its room to the title lies under "Mehr".
        assert len(during) < len(before) and during == before[: len(during)]
        expect(more(page)).to_be_visible()
    leave(page, end)
    cut = expect_title(page, width, focused=False, dots=True)
    assert cut["width"] <= wide["width"]
    if width <= 700:
        # A phone's title had a row of its own, and has what its row leaves again.
        assert not cut["whole"] and cut["width"] < wide["width"]


@ENDS
def test_a_title_past_its_share_of_the_bar_gives_the_room_back_when_the_edit_ends(editor, end):
    """I8: edited, a title takes all that folds; left, a third of the window at most."""
    page, _ = titled(editor, 1280, TOO, theme="")
    wide = expect_title(page, 1280, whole=False, focused=True)
    assert page.evaluate(BAR)["names"] == []
    leave(page, end)
    cut = expect_title(page, 1280, whole=False, dots=True, focused=False, tip=TOO)
    assert abs(cut["width"] - 0.34 * 1280) <= 1 < wide["width"] - cut["width"], (wide, cut)
    assert page.evaluate(BAR)["names"]


def test_a_bar_button_pressed_while_a_long_title_is_edited_still_gets_its_click(editor):
    """I8: the buttons the bar unfolds when the edit ends move the one under the pointer."""
    page, field = titled(editor, 1280, TOO, theme="")
    expect_title(page, 1280, focused=True)
    pin = page.get_by_label("Format und Ansicht", exact=True)
    expect(pin).to_have_attribute("aria-pressed", "true")
    pin.click()
    expect(pin).to_have_attribute("aria-pressed", "false")
    expect(field).not_to_be_focused()
    assert len(page.evaluate(BAR)["names"]) > 0
