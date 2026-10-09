"""F6 and Escape take the keys to the bars and back, and Tab scrolls to the block it picks."""

import pytest
from playwright.sync_api import expect
from test_keys_focus import OPEN, everything
from test_zoom import expect_width, scroll, width
from ui import (
    FIELD,
    LINE,
    RECT,
    RULING,
    TABLE,
    TEXT,
    at,
    box,
    centre,
    expect_picked,
    maths,
    pick,
    picked,
    picture,
    stopped,
    upload,
    user,
)

# A block of every type in `everything`, by the one a click takes, and no block at all.
PICKS = ["text", "shape", "line", "picture", "table", "ruling", "maths", "one", None]
KINDS = ["text", "shape", "line", "picture", "table", "ruling", "maths", "group"]
BAR = '[role=toolbar][aria-label="Einfügen"]'
# The part of the editor that has the focus: the sheet has it when nothing has.
PART = """() => {
    const parts = { bar: "[role=toolbar]", header: "header", panel: ".panel" };
    const on = Object.keys(parts).find((name) => document.activeElement.closest(parts[name]));
    return on ?? (document.activeElement === document.body ? "sheet" : "elsewhere");
}"""
# Whether the focus is on the first control of the part that can be pressed.
FIRST = """(part) => {
    const all = [...document.querySelector(part).querySelectorAll("button, select, input")];
    return document.activeElement === all.find((el) => !el.disabled && el.getClientRects().length);
}"""
# Whether the element lies whole in the desk, clear of the bar that floats over its lower edge.
INSIDE = """(el) => {
    const [b, d] = [el, document.querySelector(".desk")].map((e) => e.getBoundingClientRect());
    const down = b.top >= d.top - 1 && b.bottom <= d.bottom - 60;
    return down && b.left >= d.left - 1 && b.right <= d.right + 1;
}"""
LOW = {"x": 15, "y": 250, "w": 60, "h": 15}


def part(page):
    return page.evaluate(PART)


def opened(editor, name, theme=None):
    """The editor on one block of every type, with the named one picked, or none."""
    client = user()
    page = editor(*everything(client), client=client, theme=theme)
    if name:
        at(page, name).click()
        expect(at(page, name)).to_have_class("block sel")
    return page


def low(kind, client):
    """A block of the kind near the foot of the page, "a", behind a text "top" at its upper right.

    A group is "a" and "b".
    """
    top = box("top", "text", TEXT, z=3, x=150, y=20, w=45)
    if kind == "group":
        mate = {**LOW, "y": 270}
        return [
            box("a", "shape", RECT, **LOW, group=["g"]),
            box("b", "shape", RECT, z=2, **mate, group=["g"]),
            top,
        ]
    if kind == "picture":
        return [{**picture(upload(client)), "id": "a", **LOW}, top]
    if kind == "maths":
        return [box("a", "maths", maths(client), **{**LOW, "h": 12}), top]
    props = {"text": TEXT, "shape": RECT, "line": LINE, "table": TABLE, "ruling": RULING}[kind]
    return [box("a", "shape" if kind == "line" else kind, props, **LOW), top]


def zoomed(editor, kind, left=0, top=0):
    """The editor on the low blocks of the kind, four steps zoomed in, the desk scrolled so far."""
    client = user()
    page = editor(*low(kind, client), client=client)
    wide = width(page)
    for step in range(1, 5):
        page.get_by_label("Größer", exact=True).first.click()
        expect_width(page, wide * 1.25**step)
    # A button that has the focus keeps Tab.
    page.evaluate("document.activeElement.blur()")
    page.locator(".desk").evaluate("(el, to) => el.scrollTo(...to)", [left, top])
    return page


# Asked #100


@pytest.mark.parametrize("name", PICKS)
def test_f6_goes_from_the_sheet_to_the_bar(editor, name):
    page = opened(editor, name)
    was = picked(page)
    # The browser's own F6 would go to its address bar.
    assert stopped(page, "F6")
    expect(page.get_by_role("toolbar", name="Einfügen").get_by_label("Mehrere")).to_be_focused()
    assert page.evaluate(FIRST, BAR)
    assert picked(page) == was


def test_f6_finds_the_bar_of_the_other_theme(editor):
    page = opened(editor, "text", theme="")
    page.keyboard.press("F6")
    expect(page.locator(".dock").get_by_label("Mehrere")).to_be_focused()
    expect_picked(page, "text")


@pytest.mark.parametrize("name", PICKS[:-1])
def test_shift_f6_goes_from_the_sheet_to_the_panel(editor, name):
    page = opened(editor, name)
    was = picked(page)
    assert stopped(page, "Shift+F6")
    assert part(page) == "panel"
    assert page.evaluate(FIRST, ".panel")
    assert picked(page) == was


def test_shift_f6_with_nothing_picked(editor):
    # The panel's tabs are its first controls.
    page = opened(editor, None, theme="")
    page.keyboard.press("Shift+F6")
    expect(page.locator(".panel").get_by_role("tab", name="Format")).to_be_focused()
    # Blattform has no tabs there, so its panel holds nothing to press and is no stop.
    page = opened(editor, None)
    page.keyboard.press("Shift+F6")
    assert part(page) == "header"


@pytest.mark.parametrize("theme", [None, ""], ids=["leaf", "plain"])
def test_f6_goes_round_and_keeps_the_selection(editor, theme):
    page = opened(editor, "one", theme=theme)
    for keys, parts in (
        ("F6", ["bar", "header", "panel", "sheet", "bar"]),
        ("Shift+F6", ["sheet", "panel", "header", "bar", "sheet"]),
    ):
        for want in parts:
            page.keyboard.press(keys)
            assert part(page) == want
            if want != "sheet":
                assert page.evaluate(FIRST, {"bar": BAR, "header": "header"}.get(want, ".panel"))
            expect_picked(page, "one", "two")
    # The title is the header's too.
    page.get_by_label("Titel").focus()
    page.keyboard.press("F6")
    assert part(page) == "panel"
    expect(page.get_by_label("Rückgängig", exact=True)).to_be_disabled()
    # The keys are the sheet's again.
    page.keyboard.press("F6")
    page.keyboard.press("Tab")
    expect_picked(page, "text")


def test_f6_stays_out_of_a_text_and_a_dialog(editor):
    page = opened(editor, "text")
    page.keyboard.press("Enter")
    expect(page.locator(FIELD)).to_be_focused()
    assert not stopped(page, "F6")
    expect(page.locator(FIELD)).to_be_focused()
    page.keyboard.press("Escape")
    page.mouse.click(*centre(at(page, "text")), button="right")
    expect(page.get_by_role("menu")).to_be_visible()
    page.keyboard.press("F6")
    assert page.evaluate("!!document.activeElement.closest('dialog')")


CONTROLS = {
    "button of the header": lambda page: page.get_by_label("Lösungen zeigen", exact=True),
    "title": lambda page: page.get_by_label("Titel"),
    "button of the bar": lambda page: page.get_by_role("toolbar").get_by_label("Mehrere"),
    "button of the panel": lambda page: page.get_by_label("Schrift größer"),
    "select": lambda page: page.get_by_label("Schriftart"),
    "number": lambda page: page.get_by_label("X", exact=True),
    "colour": lambda page: page.locator(".panel").get_by_label("Farbe", exact=True),
}


@pytest.mark.parametrize("control", CONTROLS)
def test_escape_on_a_control_gives_the_keys_back_and_keeps_the_selection(editor, control):
    page = editor(box("a", "text", TEXT), box("b", "text", TEXT, z=2))
    pick(page, "a")
    found = CONTROLS[control](page)
    found.focus()
    expect(found).to_be_focused()
    page.keyboard.press("Escape")
    assert part(page) == "sheet"
    expect_picked(page, "a")
    expect(page.get_by_label("Rückgängig", exact=True)).to_be_disabled()
    page.keyboard.press("Tab")
    expect_picked(page, "b")
    # With the keys the sheet's, Escape selects nothing, as before.
    page.keyboard.press("Escape")
    expect_picked(page)


def test_escape_in_a_number_field_drops_its_draft(editor):
    page = editor(box("a", "text", TEXT))
    pick(page, "a")
    x = page.get_by_label("X", exact=True)
    x.click()
    page.keyboard.type("99")
    page.keyboard.press("Escape")
    expect(x).to_have_value("15")
    expect(x).not_to_be_focused()
    expect_picked(page, "a")
    expect(page.get_by_label("Rückgängig", exact=True)).to_be_disabled()


def test_escape_in_a_dialog_and_in_a_text_does_what_it_did(editor):
    page = opened(editor, "shape")
    # A menu shuts, and no more.
    page.mouse.click(*centre(at(page, "shape")), button="right")
    expect(page.get_by_role("menu")).to_be_visible()
    page.keyboard.press("Escape")
    expect(page.get_by_role("menu")).to_have_count(0)
    expect_picked(page, "shape")
    # So does the dialog for feedback, opened from a button.
    page.get_by_label("Feedback", exact=True).click()
    expect(page.locator("dialog.feedback")).to_be_visible()
    page.keyboard.press("Escape")
    expect(page.locator("dialog.feedback")).to_have_count(0)
    expect_picked(page, "shape")
    # A text, a cell and a Lineatur being written in end, and their block stays picked.
    for name in ("text", "table", "ruling"):
        pick(page, name)
        page.keyboard.press("Enter")
        expect(page.locator(OPEN)).to_be_focused()
        page.keyboard.press("Escape")
        expect(page.locator(OPEN)).to_have_count(0)
        expect_picked(page, name)
    expect(page.get_by_label("Rückgängig", exact=True)).to_be_disabled()


# Asked #97


@pytest.mark.parametrize("kind", KINDS)
def test_tab_scrolls_to_the_block_it_picks(editor, kind):
    page = zoomed(editor, kind)
    names = ["a", "b"] if kind == "group" else ["a"]
    for name in names:
        expect(at(page, name)).not_to_be_in_viewport()
    page.keyboard.press("Tab")
    expect_picked(page, *names)
    for name in names:
        expect(at(page, name)).to_be_in_viewport()
        assert at(page, name).evaluate(INSIDE)
    # Shift+Tab goes back up, and sideways to the text at the right.
    expect(at(page, "top")).not_to_be_in_viewport()
    page.keyboard.press("Shift+Tab")
    expect_picked(page, "top")
    expect(at(page, "top")).to_be_in_viewport()
    assert at(page, "top").evaluate(INSIDE)
    assert scroll(page)[0] > 0


@pytest.mark.parametrize("kind", ["text", "shape", "table", "ruling"])
def test_enter_opens_a_field_in_view(editor, kind):
    page = zoomed(editor, kind)
    page.keyboard.press("Tab")
    expect_picked(page, "a")
    page.keyboard.press("Enter")
    field = page.locator(OPEN)
    expect(field).to_be_focused()
    expect(field).to_be_in_viewport()
    assert field.evaluate(INSIDE)


def test_tab_moves_nothing_for_a_block_in_view(editor):
    page = editor(box("a", "text", TEXT, w=60), box("b", "text", TEXT, z=2, w=60))
    wide = width(page)
    for step in (1, 2):
        page.get_by_label("Größer", exact=True).first.click()
        expect_width(page, wide * 1.25**step)
    page.evaluate("document.activeElement.blur()")
    page.locator(".desk").evaluate("el => el.scrollTo(40, 40)")
    for name in ("a", "b", "a"):
        assert at(page, name).evaluate(INSIDE)
        page.keyboard.press("Tab")
        expect_picked(page, name)
        assert scroll(page) == [40, 40]
    page.keyboard.press("Shift+Tab")
    expect_picked(page, "b")
    assert scroll(page) == [40, 40]
