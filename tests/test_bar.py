"""The editor's bar is one row above a phone's width: what has no room lies behind "Mehr" (#272).

PDF, Lösungen, Rückgängig and Wiederholen never leave the window, and nothing cuts the bar off.
"""

import json
from contextlib import suppress

import pytest
from conftest import TURNED
from playwright.sync_api import TimeoutError as Late
from playwright.sync_api import expect
from ui import (
    TEXT,
    box,
    tool,  # noqa: F401  # test_variants_door imports this from here
)

THEMES = pytest.mark.parametrize("theme", [None, ""], ids=["blattform", "plain"])
# The windows the bar is pinned at: the iPad upright and on its side and a smaller one upright,
# with fingers, and a desktop and an upright window with a mouse.
PINNED = pytest.mark.parametrize(
    ("width", "height", "touch"),
    [
        (834, 1194, True),
        (768, 1024, True),
        (1194, 834, True),
        (1400, 1000, False),
        (900, 1200, False),
    ],
    ids=["ipad", "small-ipad", "ipad-turned", "desktop", "upright-mouse"],
)
EDITS = [
    "Ausschneiden",
    "Kopieren",
    "Einfügen",
    "Format übertragen",
    "Duplizieren",
    "Löschen",
    "Sperren",
    "Gruppieren",
    "Gruppierung aufheben",
    "Lösungen zeigen",
]
ZOOM = ["Kleiner", "Zoom", "Ganze Seite", "Größer"]
LAST = ["Rundgang", "Feedback", "Varianten drucken"]
# What the bar says of itself: whether the four that never fold lie in the window, whether it is
# one row that does not scroll, and the names of the commands in it that may fold.
BAR = """() => {
    const top = document.querySelector("header .top");
    const box = (el) => el.getBoundingClientRect();
    const inside = (el) => box(el).width > 0 && box(el).left >= 0 && box(el).top >= 0
        && box(el).right <= innerWidth && box(el).bottom <= innerHeight;
    const never = '.pdf button, [aria-label="Rückgängig"], [aria-label="Wiederholen"]';
    const kept = [...top.querySelectorAll(never)];
    const may = [...top.querySelectorAll(".sep ~ :is(.ib, .zoom):not(.pin, .more)")];
    return {
        kept: kept.length === 4 && kept.every(inside),
        row: top.scrollWidth <= top.clientWidth && box(top).height < 2 * box(kept[0]).height,
        names: may.map((el) => el.ariaLabel ?? el.title),
    };
}"""


def text(name, z=1, **more):
    return box(name, "text", TEXT, z=z, **more)


def resize(page, width, height):
    """Gives the window that size and waits until the page has heard of it."""
    page.set_viewport_size({"width": width, "height": height})
    # A window hears of its new size with its next frame, and WebKit of a turn a frame later.
    page.evaluate("new Promise((done) => requestAnimationFrame(() => requestAnimationFrame(done)))")


def sized(editor, *blocks, width, height, touch, **more):
    """The editor in a window of that size, with fingers or a mouse."""
    page = editor(*blocks, touch=touch, **more)
    resize(page, width, height)
    return page


def expect_fitted(page, row=True):
    """Waits until the bar keeps PDF, Lösungen, Rückgängig and Wiederholen in the window, in one row
    that does not scroll: the bar is measured anew after the window's size changes."""
    want = {"kept": True, **({"row": True} if row else {})}
    fitted = f"(want) => Object.keys(want).every((key) => ({BAR})()[key])"
    # A bar that never gets there fails below, where what it says is shown.
    with suppress(Late):
        page.wait_for_function(fitted, arg=want, timeout=2000)
    got = page.evaluate(BAR)
    assert {key: got[key] for key in want} == want, json.dumps(got, ensure_ascii=False)


def more(page):
    return page.get_by_label("Mehr", exact=True)


def menu(page):
    return page.locator("dialog.menu")


def item(page, name):
    # By its name: a command that is on or off is a `menuitemcheckbox`, the others a `menuitem`.
    return menu(page).get_by_label(name, exact=True)


def listed(page):
    """The names in "Mehr", which this opens and shuts; none where the bar holds all."""
    if not more(page).count():
        return []
    more(page).click()
    names = menu(page).locator("button").evaluate_all("els => els.map((el) => el.ariaLabel)")
    page.keyboard.press("Escape")
    expect(menu(page)).to_have_count(0)
    return names


@THEMES
@PINNED
def test_the_bar_is_one_row_with_pdf_and_undo_in_the_window(editor, theme, width, height, touch):
    """A1"""
    page = sized(editor, text("a"), width=width, height=height, touch=touch, theme=theme)
    expect_fitted(page)
    for name in ("PDF", "Lösungen"):
        expect(page.get_by_role("button", name=name, exact=True)).to_be_in_viewport(ratio=1)


@THEMES
@pytest.mark.parametrize("touch", [True, False], ids=["fingers", "mouse"])
@pytest.mark.parametrize("turned", [False, True], ids=["upright", "on-its-side"])
def test_the_bar_is_one_row_at_every_width_from_700_to_1400(editor, theme, touch, turned):
    """A2"""
    page = editor(text("a"), theme=theme, touch=touch)
    for width in sorted({*range(700, 1401, 50), 701, 1023, 1024, 1099, 1100}):
        resize(page, width, width - 250 if turned else width + 300)
        # A phone's bar, at 700, wraps as before.
        expect_fitted(page, row=width > 700)


def test_the_bar_is_measured_when_its_layout_changes_in_the_render_that_measures_it(editor):
    """A window turns narrow in the same render in which the title field loses its focus, so the bar
    is refitted and its layout changes at once. The bar must still be measured (#389).

    The window's resize event runs before its media queries are reported, so the blur lands first.
    """
    page = editor(text("a"), theme=None)
    expect_fitted(page)
    page.get_by_label("Titel").focus()
    page.evaluate('addEventListener("resize", () => document.activeElement.blur(), { once: true })')
    resize(page, 900, 1200)
    expect_fitted(page)


@THEMES
@pytest.mark.parametrize(
    "size", [(1023, 768), (1024, 768), (1024, 1366), (744, 1133), (820, 1180), (1100, 800)]
)
def test_the_bar_is_one_row_in_a_window_that_opens_at_its_size(editor, theme, size):
    """A2: Blattform's layout goes by the window's width as the editor draws, so a page that
    loads at a size can differ from one that was resized to it."""
    page = editor(text("a"), theme=theme, touch=True)
    resize(page, *size)
    page.reload()
    expect(page.locator('main.editor[data-ready="1"]')).to_be_visible()
    expect(page.locator(".block[data-id]")).to_have_count(1)
    expect_fitted(page)
    # Blattform's own layout starts at 1024 px, on its side.
    leaf = theme is None and size[0] >= 1024 and size[0] > size[1]
    expect(page.locator("main.editor.leaf")).to_have_count(int(leaf))


def test_mehr_keeps_the_focus_when_the_bar_is_fitted_anew(editor):
    """Review: "Mehr" leaves the bar while it is measured, and took the focus along."""
    page = sized(editor, text("a"), width=900, height=1200, touch=False, theme="")
    expect_fitted(page)
    more(page).focus()
    resize(page, 890, 1200)
    expect_fitted(page)
    expect(more(page)).to_be_focused()


def test_mehr_keeps_the_focus_when_blattforms_layout_goes(editor):
    """#389: upright, Blattform's layout goes, and the bar is fitted anew for that alone."""
    page = sized(editor, text("a"), width=1050, height=700, touch=False, theme=None)
    expect_fitted(page)
    expect(page.locator("main.editor.leaf")).to_have_count(1)
    more(page).focus()
    resize(page, 1050, 1300)
    expect_fitted(page)
    expect(page.locator("main.editor.leaf")).to_have_count(0)
    expect(more(page)).to_be_focused()


def test_mehr_gets_the_focus_back_when_the_bar_was_fitted_anew_under_its_menu(editor):
    """#287: the bar's width changes under the open menu, as when its type loads late. "Mehr" left
    the bar to be measured, and the menu handed the focus back to a button that was gone."""
    page = editor(text("a"), theme="", touch=True)
    expect_fitted(page)
    more(page).focus()
    page.keyboard.press("Enter")
    expect(menu(page)).to_be_visible()
    # The bar hears of its new width with the next frame.
    page.evaluate(
        """() => {
            const top = document.querySelector("header .top");
            top.style.width = `${top.clientWidth - 30}px`;
            return new Promise((done) => requestAnimationFrame(() => requestAnimationFrame(done)));
        }"""
    )
    page.keyboard.press("Escape")
    expect(menu(page)).to_have_count(0)
    expect_fitted(page)
    expect(more(page)).to_be_focused()


def test_the_bar_is_fitted_anew_when_a_right_click_beside_the_menu_shuts_it(editor):
    """Review: the bar waited under the open menu, and a right click beside it shuts the menu with
    no close of its own. The bar is measured then, or it stays too wide for its place."""
    page = editor(text("a"), theme="", touch=True)
    expect_fitted(page)
    more(page).focus()
    page.keyboard.press("Enter")
    expect(menu(page)).to_be_visible()
    # Further than the bar's slack: only a bar measured anew fits. It hears with the next frame.
    box = page.evaluate(
        """() => {
            const top = document.querySelector("header .top");
            top.style.width = `${top.clientWidth - 250}px`;
            const { x, y } = top.getBoundingClientRect();
            const frame = (then) => requestAnimationFrame(then);
            return new Promise((done) => frame(() => frame(() => done({ x, y }))));
        }"""
    )
    page.mouse.click(box["x"] + 5, box["y"] + 5, button="right")
    expect(menu(page)).to_have_count(0)
    expect_fitted(page)


def test_a_turn_gives_the_focus_back_to_mehr_that_the_keys_opened(editor):
    """Review"""
    page = editor(text("a"), theme="", touch=True)
    expect_fitted(page)
    more(page).focus()
    page.keyboard.press("Enter")
    expect(menu(page)).to_be_visible()
    resize(page, **TURNED)
    expect(menu(page)).to_have_count(0)
    expect_fitted(page)
    expect(more(page)).to_be_focused()


@THEMES
@PINNED
def test_the_bar_and_mehr_hold_every_command_once(editor, theme, width, height, touch):
    """A3"""
    page = sized(editor, text("a"), width=width, height=height, touch=touch, theme=theme)
    expect_fitted(page)
    # Blattform's own layout has the zoom over the desk, not in the bar.
    leaf = page.locator("main.editor.leaf").count() == 1
    assert leaf == (theme is None and width > height)
    want = [*EDITS, *([] if leaf else ZOOM), *LAST]
    # The bar's zoom button is titled "Zoom", as is its command in "Mehr".
    in_bar = page.evaluate(BAR)["names"]
    in_menu = listed(page)
    assert in_bar + in_menu == want
    assert all(name in in_bar for name in ZOOM) or not any(name in in_bar for name in ZOOM)
    # No command is in the page twice, by any name.
    for name in want:
        named = f'button:is([aria-label="{name}"], .zoom[title="{name}"]):not(.dock *)'
        assert page.locator(named).count() == (name in in_bar)


# The name under a button the pointer rests on: its box in the window, and the first thing
# around the button that cuts it off, if any.
TIP = """(el) => {
    const tip = getComputedStyle(el, "::after");
    if (tip.content === "none" || tip.position !== "absolute") return null;
    const on = el.getBoundingClientRect();
    const px = (...names) => names.reduce((sum, name) => sum + parseFloat(tip[name]), 0);
    const width = px("width", "paddingLeft", "paddingRight");
    const height = px("height", "paddingTop", "paddingBottom");
    const left = on.left + on.width / 2 - width / 2 + px("marginLeft");
    const top = on.bottom + px("top") - on.height;
    const box = { left, top, right: left + width, bottom: top + height };
    let cut = null;
    for (let up = el.parentElement; up && !cut; up = up.parentElement) {
        const look = getComputedStyle(up);
        const around = up.getBoundingClientRect();
        const clips = [look.overflowX, look.overflowY].some((flow) => flow !== "visible");
        const holds = around.left <= box.left && around.right >= box.right
            && around.top <= box.top && around.bottom >= box.bottom;
        if (clips && !holds) cut = up.className || up.tagName;
    }
    return { content: tip.content, box, cut, window: [innerWidth, innerHeight] };
}"""


# The `--shift` the bar and the dock hold, and whether a name makes the window scroll sideways.
HELD = """() => ({
    shifts: [...document.querySelectorAll(".top, .dock")]
        .map((el) => el.style.getPropertyValue("--shift")),
    scrolls: document.documentElement.scrollWidth > innerWidth,
})"""
