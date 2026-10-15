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
        // WebKit counts a whole title a pixel wider than its field.
        whole: el.scrollWidth <= el.clientWidth + 1,
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


STAND_IN = "Unbenanntes Blatt"
# Where a click lands inside the text: a share of the way along it, by the field's own font.
AT_SHARE = """(share) => {
    const el = document.querySelector("header input[aria-label=Titel]");
    const style = getComputedStyle(el);
    const ctx = document.createElement("canvas").getContext("2d");
    ctx.font = style.font;
    const width = ctx.measureText(el.value).width;
    const left = el.getBoundingClientRect().left + parseFloat(style.paddingLeft);
    return { x: left + share * width, y: el.getBoundingClientRect().top + el.offsetHeight / 2 };
}"""
SELECTED = """() => {
    const el = document.querySelector("header input[aria-label=Titel]");
    return [el.selectionStart, el.selectionEnd, el.value.length, el.value];
}"""


def with_stand_in(editor, value=STAND_IN):
    """The editor with a sheet whose title is the stand-in, the field left with no focus."""
    page = sized(editor, text("a"), width=1280, height=1024, touch=False)
    field = page.get_by_label("Titel")
    field.fill(value)
    expect(field).to_be_focused()
    leave(page, "click")
    expect(field).not_to_have_value("")
    return page, field


def click_inside(page):
    """A click at 40% of the field's text, the place a teacher's click lands in a title."""
    at = page.evaluate(AT_SHARE, 0.4)
    page.mouse.click(at["x"], at["y"])


def test_a_click_on_the_stand_in_title_picks_it_whole_and_typing_replaces_it(editor):
    """#364: the stand-in is picked whole, so typing replaces it and the typed title is saved."""
    page, field = with_stand_in(editor)
    click_inside(page)
    expect(field).to_be_focused()
    start, end, length, _ = page.evaluate(SELECTED)
    assert (start, end) == (0, length) == (0, len(STAND_IN)), (start, end, length)
    page.keyboard.type("Mein Titel")
    page.keyboard.press("Enter")
    expect(field).to_have_value("Mein Titel")
    expect(page.locator("header .hint")).to_have_text("Gespeichert")
    sheet_id = page.url.rsplit("/", 1)[1]
    saved = page.request.get(f"{page.url.split('/blatt/')[0]}/api/sheets/{sheet_id}").json()
    assert saved["title"] == "Mein Titel"


def test_a_click_on_a_real_title_puts_the_caret_where_it_fell(editor):
    """#364: any other title keeps the caret where the click fell."""
    page = sized(editor, text("a"), width=1280, height=1024, touch=False)
    field = page.get_by_label("Titel")
    expect(field).to_have_value("Plus bis 20")
    click_inside(page)
    expect(field).to_be_focused()
    start, end, length, _ = page.evaluate(SELECTED)
    assert start == end and 0 < start < length, (start, end, length)


def test_tab_into_the_stand_in_title_picks_it_whole(editor):
    """#364, implied: keyboard focus picks the stand-in whole too."""
    page, field = with_stand_in(editor)
    page.get_by_label("Titel").focus()
    page.keyboard.press("Tab")
    page.keyboard.press("Shift+Tab")
    expect(field).to_be_focused()
    start, end, length, _ = page.evaluate(SELECTED)
    assert (start, end) == (0, length) == (0, len(STAND_IN)), (start, end, length)


def test_a_second_click_on_the_focused_stand_in_title_places_the_caret(editor):
    """#364, implied: once the field has the focus, a click places the caret where it fell."""
    page, field = with_stand_in(editor)
    click_inside(page)
    expect(field).to_be_focused()
    click_inside(page)
    start, end, length, _ = page.evaluate(SELECTED)
    assert start == end and 0 < start < length, (start, end, length)


def test_a_stand_in_with_spaces_around_it_is_picked_whole(editor):
    """#364: the stand-in counts with spaces around it, as the field keeps them."""
    page, field = with_stand_in(editor, value=f"  {STAND_IN} ")
    click_inside(page)
    expect(field).to_be_focused()
    start, end, length, _ = page.evaluate(SELECTED)
    assert (start, end) == (0, length), (start, end, length)


def test_escape_after_the_pick_keeps_the_stand_in(editor):
    """#364: a pick that is given up with Escape leaves the stand-in as it was."""
    page, field = with_stand_in(editor)
    click_inside(page)
    expect(field).to_be_focused()
    page.keyboard.press("Escape")
    expect(field).not_to_be_focused()
    expect(field).to_have_value(STAND_IN)


def test_a_double_click_on_a_real_title_selects_a_word(editor):
    """#364: a double click on a real title still selects the word under it."""
    page = sized(editor, text("a"), width=1280, height=1024, touch=False)
    field = page.get_by_label("Titel")
    at = page.evaluate(AT_SHARE, 0.6)
    page.mouse.dblclick(at["x"], at["y"])
    expect(field).to_be_focused()
    start, end, _, value = page.evaluate(SELECTED)
    assert start < end and value[start:end] in {"Plus", "bis", "20"}, (start, end, value)


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
    with: 120 px, a third of a phone's window."""
    title = "TR4 Zwei Seiten"
    page, _ = titled(editor, 360, title)
    leave(page, "Enter")
    got = expect_title(page, 360, whole=True, focused=False, tip=title)
    assert got["width"] >= 120, got


def test_blattforms_long_title_leaves_commands_in_the_bar(editor):
    """A14, I8: beside the green panel the bar is short, and a title with no focus may take less
    of it: cut, it folds some commands and not all."""
    page, _ = titled(editor, 1280, TOO)
    leave(page, "Enter")
    expect_title(page, 1280, whole=False, dots=True, focused=False, tip=TOO)
    assert page.evaluate(BAR)["names"][:3] == ["Ausschneiden", "Kopieren", "Einfügen"]
