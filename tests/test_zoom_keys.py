"""Ctrl and + or - zoom the sheet one step, Ctrl+Alt+O fits the page, and a field keeps its keys."""

import pytest
from playwright.sync_api import expect
from test_zoom import expect_fitted, expect_percent, expect_width, places, settled, width
from ui import FIELD, TABLE, TEXT, at, box, expect_picked, pick

# After the app's own listeners: whether the last keydown was called off by the page.
PREVENTED = (
    "addEventListener('keydown', (e) => setTimeout(() => "
    "(window.prevented = e.defaultPrevented)), true)"
)
# Where the zoom keys zoom nothing: an open text, a table cell, the title, a panel's number
# field, the zoom's list.
FIELDS = ["text", "cell", "title", "number", "list"]


def prevented(page):
    """Whether the last keydown was called off, once it has arrived."""
    page.wait_for_function("window.prevented !== undefined")
    return page.evaluate(
        "() => { const was = window.prevented; delete window.prevented; return was; }"
    )


def dispatch(page, key, code, alt=False, altgr=False):
    """A keydown with Ctrl on the focused element. AltGr comes as Ctrl with Alt, as on Windows."""
    page.evaluate(
        """([key, code, alt, altgr]) => document.activeElement.dispatchEvent(
            new KeyboardEvent('keydown', { key, code, ctrlKey: true, altKey: alt,
                modifierAltGraph: altgr, bubbles: true, cancelable: true }))""",
        [key, code, alt, altgr],
    )


def cell(page, name, n):
    return at(page, name).locator(f'.table > div[data-cell="{n}"]')


@pytest.mark.parametrize("keys", ["Control+Equal", "Control+Shift+Equal", "Control+NumpadAdd"])
def test_ctrl_plus_zooms_in_one_step(editor, keys):
    """Ctrl and + zoom one step in, as Größer does."""
    page = editor(box("a", "text", TEXT))
    wide = width(page)
    page.keyboard.press(keys)
    expect_width(page, wide * 1.25)
    expect_percent(page)


@pytest.mark.parametrize("keys", ["Control+Minus", "Control+NumpadSubtract"])
def test_ctrl_minus_zooms_out_one_step(editor, keys):
    """Ctrl and - zoom one step out, as Kleiner does."""
    page = editor(box("a", "text", TEXT))
    wide = width(page)
    page.keyboard.press(keys)
    expect_width(page, wide / 1.25)
    expect_percent(page)


def test_german_plus_and_minus_zoom(editor):
    """The keys of a German keyboard, which Playwright cannot press on a US layout."""
    page = editor(box("a", "text", TEXT))
    wide = width(page)
    dispatch(page, "+", "BracketRight")
    expect_width(page, wide * 1.25)
    dispatch(page, "-", "Slash")
    expect_width(page, wide)


def test_ctrl_alt_o_fits_the_page(editor):
    """Ctrl+Alt+O does what the button Ganze Seite does."""
    page = editor(box("a", "text", TEXT))
    page.keyboard.press("Control+Alt+O")
    expect_fitted(page, 0, 210, 297)
    expect_percent(page)


def test_a_mac_option_o_fits_the_page(editor):
    """On a Mac Option+O types ø, but the key is still O."""
    page = editor(box("a", "text", TEXT))
    dispatch(page, "ø", "KeyO", alt=True)
    expect_fitted(page, 0, 210, 297)


def test_altgr_o_and_plus_zoom_nothing(editor):
    """With AltGr the keys type characters: AltGr+O and AltGr++ give ö and ~ on German Windows."""
    page = editor(box("a", "text", TEXT))
    wide = width(page)
    dispatch(page, "o", "KeyO", alt=True, altgr=True)
    dispatch(page, "+", "BracketRight", alt=True, altgr=True)
    settled(page)
    assert width(page) == pytest.approx(wide, abs=1)


def test_the_browsers_zoom_is_called_off(editor):
    """The keys zoom the sheet and not the browser. Ctrl+O stays the browser's."""
    page = editor(box("a", "text", TEXT))
    page.evaluate(f"window.{PREVENTED}")
    for keys in ("Control+Equal", "Control+Minus", "Control+Alt+O"):
        page.keyboard.press(keys)
        assert prevented(page), keys
    page.keyboard.press("Control+o")
    assert not prevented(page)


@pytest.mark.parametrize("where", FIELDS)
def test_a_field_keeps_the_zoom_keys(editor, where):
    """In a field or the zoom's list the keys zoom nothing, and never the browser's window."""
    page = editor(box("a", "text", TEXT), box("t", "table", TABLE, z=2, x=60, y=120, w=60, h=40))
    if where == "text":
        pick(page, "a")
        page.keyboard.press("Enter")
        field = page.locator(FIELD)
    elif where == "cell":
        pick(page, "t")
        cell(page, "t", 0).dblclick()
        field = at(page, "t").locator("textarea")
    elif where == "title":
        field = page.get_by_label("Titel", exact=True)
    elif where == "list":
        page.locator("button.zoom").first.click()
        field = page.get_by_label("Zoom in Prozent")
    else:
        pick(page, "a")
        field = page.locator("input.mm").first
    field.click()
    expect(field).to_be_focused()
    wide = width(page)
    page.evaluate(f"window.{PREVENTED}")
    for keys in ("Control+Equal", "Control+Minus"):
        page.keyboard.press(keys)
        assert prevented(page), keys
    # Ctrl+Alt+O has no meaning for the browser: the field keeps it.
    page.keyboard.press("Control+Alt+O")
    assert not prevented(page)
    settled(page)
    assert width(page) == pytest.approx(wide, abs=1)
    expect(field).to_be_focused()


@pytest.mark.parametrize("kind", ["text", "table"])
def test_a_zoom_key_keeps_the_pick_and_is_no_undo_step(editor, kind):
    """The picked block stays picked, and Ctrl+Z still takes back the last move, not the zoom."""
    page = editor(box("a", "text", TEXT), box("t", "table", TABLE, z=2, x=60, y=120, w=60, h=40))
    name = "a" if kind == "text" else "t"
    pick(page, name)
    wide = width(page)
    # Where the block lies, as shares of the page's width, so that a zoom leaves it as it is.
    before = [v / wide for v in places(page, name)[0]]
    page.keyboard.press("ArrowRight")
    settled(page)
    moved = [v / width(page) for v in places(page, name)[0]]
    assert moved != pytest.approx(before, abs=1e-3)
    page.keyboard.press("Control+Equal")
    expect_width(page, wide * 1.25)
    expect_picked(page, name)
    page.keyboard.press("Control+z")
    settled(page)
    assert [v / width(page) for v in places(page, name)[0]] == pytest.approx(before, abs=1e-3)


def test_the_keys_stop_where_the_buttons_stop(editor):
    """The keys stop at 4 times the page's width and at a quarter of it, as the buttons do."""
    page = editor(box("a", "text", TEXT))
    wide = width(page)
    for notch in range(1, 8):
        page.keyboard.press("Control+Equal")
        expect_width(page, wide * min(4, 1.25**notch))
    settled(page)
    assert width(page) == pytest.approx(wide * 4, abs=2)
    for notch in range(1, 15):
        page.keyboard.press("Control+Minus")
        expect_width(page, wide * max(0.25, 1.25 ** (7 - notch)))
    settled(page)
    assert width(page) == pytest.approx(wide * 0.25, abs=2)
