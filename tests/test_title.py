"""The bar shows as much of a sheet's title as it has room for (#318).

A title that is cut ends in three dots, shows whole under the pointer, and whole while it is
edited: the bar then folds more of its commands under "Mehr".
"""

import json

import pytest
from playwright.sync_api import expect
from test_bar import BAR, expect_fitted, more, sized, text
from ui import at, pick

WIDTHS = pytest.mark.parametrize("width", [1280, 820, 360])
ENDS = pytest.mark.parametrize("end", ["Enter", "Escape", "click"])
# One that has room at any of the widths, one that a row of 360 px holds, one that no bar holds
# with its commands in it, and one of 80 wide letters, which no bar holds at all.
SHORT = "TR3 Bild"
ROW = "Rechnen bis 100 mit Zehnerübergang"
LONG = "Die Geschichte vom kleinen Igel, der eines Nachts nicht schlafen wollte"
TOO = "Mm" * 40
# Whether the bar holds a command that may fold.
UNFOLDED = f"() => ({BAR})().names.length > 0"
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
        # At 1280 the layout is Blattform's own, whose shorter bar gives a title a fifth.
        names = page.evaluate(BAR)["names"]
        most = (0.2 if width == 1280 else 0.34) * width
        assert abs(got["width"] - most) <= 1 or not names, json.dumps([got, names])


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
    # After a click the bar unfolds when the press is through, a moment later.
    page.wait_for_function(UNFOLDED, timeout=2000)


def test_a_bar_button_pressed_while_a_long_title_is_edited_still_gets_its_click(editor):
    """I8: the buttons the bar unfolds when the edit ends move the one under the pointer."""
    page, field = titled(editor, 1280, TOO, theme="")
    expect_title(page, 1280, focused=True)
    pin = page.get_by_label("Format und Ansicht", exact=True)
    expect(pin).to_have_attribute("aria-pressed", "true")
    pin.click()
    expect(pin).to_have_attribute("aria-pressed", "false")
    expect(field).not_to_be_focused()
    page.wait_for_function(UNFOLDED, timeout=2000)


def test_a_press_that_ends_the_edit_finds_its_button_still_under_the_pointer(editor):
    """I8: Rückgängig lies right after the title and moves with its end. A press there takes the
    focus from the title when the mouse button goes down, and the bar waits until it is up."""
    page, field = titled(editor, 1280, SHORT, theme="")
    pick(page, "a")
    page.keyboard.press("Delete")
    expect(page.locator(".block[data-id]")).to_have_count(0)
    field.fill(TOO)
    expect_title(page, 1280, focused=True)
    undo = page.get_by_label("Rückgängig", exact=True)
    was = undo.bounding_box()
    # A real mouse, which goes up where it went down: a click by its locator would aim anew.
    page.mouse.move(was["x"] + was["width"] / 2, was["y"] + was["height"] / 2)
    page.mouse.down()
    page.mouse.up()
    expect(at(page, "a")).to_be_visible()
    # The button did move, once the press was over and the bar unfolded what has room again.
    cut = expect_title(page, 1280, whole=False, dots=True, focused=False)
    assert abs(cut["width"] - 0.34 * 1280) <= 1, cut
    page.wait_for_function(UNFOLDED, timeout=2000)
    assert undo.bounding_box()["x"] < was["x"] - 40


def test_a_phones_title_has_a_third_of_the_window_and_shows_whole_in_it(editor):
    """A14: where a row breaks is up to the window alone, and so is the room the title starts
    with: as much as it may take in a wider window."""
    title = "TR4 Zwei Seiten"
    page, _ = titled(editor, 360, title)
    leave(page, "Enter")
    got = expect_title(page, 360, whole=True, focused=False, tip=title)
    assert got["width"] >= 0.34 * 360 - 1, got


def test_blattforms_long_title_leaves_commands_in_the_bar(editor):
    """A14, I8: beside the green panel the bar is short, and a title with no focus may take less
    of it: cut, it folds some commands and not all."""
    page, _ = titled(editor, 1280, TOO)
    leave(page, "Enter")
    expect_title(page, 1280, whole=False, dots=True, focused=False, tip=TOO)
    assert page.evaluate(BAR)["names"][:3] == ["Ausschneiden", "Kopieren", "Einfügen"]
