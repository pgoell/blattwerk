"""The editor's bar is one row above a phone's width: what has no room lies behind "Mehr" (#272).

PDF, Lösungen, Rückgängig and Wiederholen never leave the window, and nothing cuts the bar off.
"""

import json
from contextlib import suppress

import pytest
from conftest import IPAD, TURNED
from playwright.sync_api import TimeoutError as Late
from playwright.sync_api import expect
from ui import (
    FIELD,
    TEXT,
    apart,
    at,
    box,
    centre,
    expect_picked,
    maths,
    pick,
    saved,
    swipe,
    tool,
    user,
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
ZOOM = ["Kleiner", "Seitenbreite", "Ganze Seite", "Größer"]
LAST = ["Rundgang", "Feedback"]
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
    in_bar = page.evaluate(BAR)["names"]
    in_menu = listed(page)
    assert in_bar + in_menu == want
    assert all(name in in_bar for name in ZOOM) or not any(name in in_bar for name in ZOOM)
    # No command is in the page twice, by any name.
    for name in want:
        named = f'button:is([aria-label="{name}"], .zoom[title="{name}"]):not(.dock *)'
        assert page.locator(named).count() == (name in in_bar)


def test_a_command_in_mehr_is_off_where_its_button_is_off(editor):
    """A3"""
    page = sized(editor, text("a"), text("b", 2), width=701, height=1000, touch=False, theme="")
    expect_fitted(page)
    needs = ["Format übertragen", "Duplizieren", "Löschen", "Sperren"]
    more(page).click()
    for name in (*needs, "Gruppieren", "Gruppierung aufheben"):
        expect(item(page, name)).to_be_disabled()
    for name in ("Lösungen zeigen", *ZOOM, *LAST):
        expect(item(page, name)).to_be_enabled()
    page.keyboard.press("Escape")
    pick(page, "a")
    more(page).click()
    for name in needs:
        expect(item(page, name)).to_be_enabled()
    expect(item(page, "Gruppieren")).to_be_disabled()
    page.keyboard.press("Escape")
    pick(page, "a", "b")
    more(page).click()
    expect(item(page, "Gruppieren")).to_be_enabled()
    expect(item(page, "Gruppierung aufheben")).to_be_disabled()


def test_commands_run_from_mehr_do_what_their_buttons_do(editor):
    """A3"""
    client = user()
    blocks = [text("a"), box("m", "maths", maths(client), z=2)]
    page = sized(editor, *blocks, client=client, width=768, height=1024, touch=True, theme="")
    expect_fitted(page)
    assert "Kopieren" not in page.evaluate(BAR)["names"]
    at(page, "a").tap()
    expect_picked(page, "a")
    tool(page, "Kopieren").tap()
    expect(menu(page)).to_have_count(0)
    tool(page, "Einfügen").tap()
    expect(page.locator(".block[data-id]")).to_have_count(3)
    tool(page, "Löschen").tap()
    expect(page.locator(".block[data-id]")).to_have_count(2)
    # The answers show in the sums.
    answer = at(page, "m").locator("u").first
    expect(answer).to_have_text("")
    tool(page, "Lösungen zeigen").tap()
    expect(answer).not_to_have_text("")
    width = page.locator(".sheet").first.bounding_box()["width"]
    tool(page, "Größer").tap()
    page.wait_for_function(
        "(was) => document.querySelector('.sheet').getBoundingClientRect().width > was * 1.2",
        arg=width,
    )
    tool(page, "Rundgang").tap()
    expect(page.locator(".tour h2")).to_have_text("Willkommen bei Blattomat")
    page.locator(".tour").get_by_text("Beenden").tap()
    tool(page, "Feedback").tap()
    form = page.locator("dialog.feedback")
    expect(form).to_be_visible()
    # What is written in the form stays when the bar is fitted anew under it.
    form.get_by_label("Schreiben").fill("zu eng")
    resize(page, **TURNED)
    expect_fitted(page)
    expect(form).to_be_visible()
    expect(form.get_by_label("Schreiben")).to_have_value("zu eng")
    resize(page, **IPAD)
    expect_fitted(page)
    expect(form.get_by_label("Schreiben")).to_have_value("zu eng")


def test_format_uebertragen_from_mehr_stays_on_until_it_is_picked_again(editor):
    """A3: a menu has no double click, so the brush picked there paints block after block."""
    client = user()
    blocks = apart(
        box("a", "text", {**TEXT, "bold": True}), text("b", 2), text("c", 3), text("d", 4)
    )
    page = editor(*blocks, client=client, touch=True, theme="")
    expect_fitted(page)
    assert "Format übertragen" not in page.evaluate(BAR)["names"]
    at(page, "a").tap()
    expect_picked(page, "a")
    tool(page, "Format übertragen").tap()
    brushing = page.locator("main.editor.brush")
    expect(brushing).to_have_count(1)
    for name in "bc":
        at(page, name).tap()
        expect_picked(page, name)
        expect(brushing).to_have_count(1)
    # The item shows that the brush is on, and picking it again puts the brush down.
    more(page).tap()
    expect(item(page, "Format übertragen")).to_have_attribute("aria-checked", "true")
    item(page, "Format übertragen").tap()
    expect(brushing).to_have_count(0)
    at(page, "d").tap()
    expect_picked(page, "d")
    more(page).tap()
    expect(item(page, "Format übertragen")).to_have_attribute("aria-checked", "false")
    page.keyboard.press("Escape")
    look = {b["id"]: b["props"].get("bold", False) for b in saved(page, client)}
    assert look == {"a": True, "b": True, "c": True, "d": False}


def test_mehr_opens_by_a_tap(editor):
    """A4"""
    page = editor(text("a"), touch=True)
    expect_fitted(page)
    more(page).tap()
    expect(menu(page)).to_be_visible()
    expect(more(page)).to_have_attribute("aria-expanded", "true")
    # The menu lies in the window, under its button.
    place, under = menu(page).bounding_box(), more(page).bounding_box()
    assert place["y"] >= under["y"] + under["height"]
    assert place["x"] >= 0 and place["x"] + place["width"] <= IPAD["width"]
    assert place["y"] + place["height"] <= IPAD["height"]
    # A tap beside it shuts it.
    page.touchscreen.tap(100, 900)
    expect(menu(page)).to_have_count(0)


def test_mehr_opens_and_runs_by_the_keys(editor):
    """A4"""
    page = sized(editor, text("a"), width=900, height=1200, touch=False, theme="")
    expect_fitted(page)
    page.get_by_label("Titel").focus()
    for _ in range(30):
        if more(page).evaluate("el => el === document.activeElement"):
            break
        page.keyboard.press("Tab")
    expect(more(page)).to_be_focused()
    for key in ("Enter", "Space"):
        page.keyboard.press(key)
        expect(menu(page)).to_be_visible()
        items = menu(page).locator("button")
        # The first command that is on has the focus, and the arrows walk from it.
        expect(items.nth(0)).to_be_focused()
        page.keyboard.press("ArrowDown")
        expect(items.nth(1)).to_be_focused()
        page.keyboard.press("ArrowUp")
        expect(items.nth(0)).to_be_focused()
        page.keyboard.press("Escape")
        expect(menu(page)).to_have_count(0)
        expect(more(page)).to_be_focused()
    # Enter runs the command the focus is on.
    page.keyboard.press("Enter")
    expect(item(page, "Lösungen zeigen")).to_be_focused()
    page.keyboard.press("Enter")
    expect(menu(page)).to_have_count(0)
    expect(more(page)).to_be_focused()
    page.keyboard.press("Enter")
    expect(item(page, "Lösungen zeigen")).to_have_attribute("aria-checked", "true")


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


# The `--shift` the bar and the dock hold, and whether a name makes the window scroll sideways.
HELD = """() => ({
    shifts: [...document.querySelectorAll(".top, .dock")]
        .map((el) => el.style.getPropertyValue("--shift")),
    scrolls: document.documentElement.scrollWidth > innerWidth,
})"""


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


def test_a_command_from_mehr_acts_on_the_whole_selection_as_one_step_of_undo(editor):
    """I1"""
    page = sized(editor, text("a"), text("b", 2), width=768, height=1024, touch=False, theme="")
    expect_fitted(page)
    undo = page.get_by_label("Rückgängig", exact=True)
    pick(page, "a", "b")
    tool(page, "Löschen").click()
    expect(page.locator(".block[data-id]")).to_have_count(0)
    undo.click()
    expect(page.locator(".block[data-id]")).to_have_count(2)
    expect(undo).to_be_disabled()


def test_mehr_shows_what_is_on(editor):
    """I2"""
    blocks = [text("a"), text("b", 2, locked=True)]
    page = sized(editor, *blocks, width=768, height=1024, touch=False, theme="")
    expect_fitted(page)
    more(page).click()
    expect(item(page, "Lösungen zeigen")).to_have_attribute("aria-checked", "false")
    item(page, "Lösungen zeigen").click()
    more(page).click()
    expect(item(page, "Lösungen zeigen")).to_have_attribute("aria-checked", "true")
    # A tick stands at the end of its row.
    tick = "el => getComputedStyle(el, '::after').content"
    assert item(page, "Lösungen zeigen").evaluate(tick) == '"✓"'
    assert item(page, "Kleiner").evaluate(tick) == "none"
    expect(item(page, "Sperren")).to_be_visible()
    page.keyboard.press("Escape")
    pick(page, "b")
    more(page).click()
    expect(item(page, "Entsperren")).to_be_enabled()
    expect(item(page, "Sperren")).to_have_count(0)
    item(page, "Entsperren").click()
    more(page).click()
    expect(item(page, "Sperren")).to_be_enabled()


@pytest.mark.parametrize("touch", [True, False], ids=["fingers", "mouse"])
def test_a_text_stays_open_with_its_caret_while_mehr_opens_and_shuts(editor, touch):
    """I3"""
    page = sized(editor, text("a"), width=834, height=1194, touch=touch, theme="")
    expect_fitted(page)
    if touch:
        at(page, "a").tap()
        expect_picked(page, "a")
        # A second tap on the selected text opens it; see test_ipad for the swipe.
        swipe(page, centre(at(page, "a")))
    else:
        at(page, "a").dblclick()
    expect(page.locator(FIELD)).to_be_focused()
    page.keyboard.press("End")
    page.keyboard.type("x")
    if touch:
        more(page).tap()
    else:
        more(page).click()
    expect(menu(page)).to_be_visible()
    page.keyboard.press("Escape")
    expect(menu(page)).to_have_count(0)
    expect(page.locator(FIELD)).to_be_focused()
    page.keyboard.type("y")
    expect(page.locator(FIELD)).to_have_text("Halloxy")
    # A command picked there ends the writing, as its button in the bar does.
    tool(page, "Lösungen zeigen").click()
    expect(page.locator(FIELD)).to_have_count(0)
    expect(at(page, "a")).to_contain_text("Halloxy")


@THEMES
def test_where_all_fits_there_is_no_mehr(editor, theme):
    """I4"""
    page = editor(text("a"), theme=theme)
    expect_fitted(page)
    expect(more(page)).to_have_count(0)
    expect(page.get_by_label("Feedback", exact=True)).to_be_visible()


@THEMES
def test_a_turn_of_the_ipad_shuts_mehr_and_fits_the_bar_anew(editor, theme):
    """I4"""
    page = editor(text("a"), theme=theme, touch=True)
    expect_fitted(page)
    upright = page.evaluate(BAR)["names"]
    for size in (TURNED, IPAD):
        more(page).tap()
        expect(menu(page)).to_be_visible()
        resize(page, **size)
        expect(menu(page)).to_have_count(0)
        expect_fitted(page)
        expect(more(page)).to_have_attribute("aria-expanded", "false")
    assert page.evaluate(BAR)["names"] == upright
    assert listed(page) == [*EDITS, *ZOOM, *LAST][len(upright) :]


@pytest.mark.parametrize("size", [(834, 1194), (768, 1024)], ids=["ipad", "small-ipad"])
def test_a_long_title_pushes_neither_pdf_nor_undo_out_of_the_window(editor, size):
    """I5"""
    page = sized(editor, text("a"), width=size[0], height=size[1], touch=True, theme="")
    expect_fitted(page)
    before = page.evaluate(BAR)["names"]
    title = page.get_by_label("Titel")
    title.fill("W" * 80)
    expect(title).to_have_value("W" * 80)
    expect_fitted(page)
    assert page.evaluate(BAR)["names"] == before
