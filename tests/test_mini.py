"""The mini toolbar beside the block menu: turn, align and the brush."""

import pytest
from playwright.sync_api import expect
from test_menu import GROUP, corner, menu, props, right, right_thumb, texts
from test_pages import three
from test_painter import expect_brush, held
from ui import LINE, RECT, TEXT, angle, at, box, expect_picked, pick, user

MINI = [
    "Linksdrehung 90°",
    "Rechtsdrehung 90°",
    "Links",
    "Mitte waagerecht",
    "Rechts",
    "Oben",
    "Mitte senkrecht",
    "Unten",
    "Format übertragen",
]
# The buttons that change the blocks: a click on one is one undo step.
CHANGES = MINI[:8]


def mini(page):
    return page.get_by_role("toolbar", name="Minisymbolleiste")


def tool(page, name):
    return mini(page).get_by_role("button", name=name, exact=True)


def rect(page, name):
    """The box a block or the toolbar takes on the screen, as a dict."""
    css = {"toolbar": '[aria-label="Minisymbolleiste"]', "menu": "dialog.menu"}.get(
        name, f'[data-id="{name}"]'
    )
    box = page.locator(css).first.evaluate("el => el.getBoundingClientRect().toJSON()")
    return {side: box[side] for side in ("left", "top", "right", "bottom")}


def apart(a, b):
    """Two boxes that share no point of the screen."""
    return (
        a["right"] <= b["left"]
        or b["right"] <= a["left"]
        or a["bottom"] <= b["top"]
        or b["bottom"] <= a["top"]
    )


def test_the_block_menu_shows_the_mini_toolbar(editor):
    """A5"""
    page = editor(*texts("a"))
    right(page, "a")
    expect(mini(page)).to_be_visible()
    expect(mini(page).get_by_role("button")).to_have_count(len(MINI))
    for name in MINI:
        expect(tool(page, name)).to_be_visible()
        expect(tool(page, name)).to_have_attribute("title", name)


@pytest.mark.parametrize("name", CHANGES)
def test_a_mini_buttons_change_is_one_undo_step(editor, name):
    """A6"""
    page = editor(box("a", "text", TEXT, x=60, y=60))
    before = rect(page, "a")
    right(page, "a")
    tool(page, name).click()
    expect(menu(page)).to_have_count(0)
    expect(page.get_by_role("button", name="Rückgängig")).to_be_enabled()
    page.keyboard.press("Control+z")
    expect(page.get_by_role("button", name="Rückgängig")).to_be_disabled()
    expect(page.get_by_role("button", name="Wiederholen")).to_be_enabled()
    assert rect(page, "a") == before


def test_a_mini_turn_works_on_a_tapped_button(editor):
    """A7"""
    page = editor(*texts("a"), touch=True)
    right(page, "a")
    tool(page, "Rechtsdrehung 90°").tap()
    expect(menu(page)).to_have_count(0)
    expect(page.get_by_role("button", name="Rückgängig")).to_be_enabled()
    assert angle(page, "a") == 90


@pytest.mark.parametrize("top", [False, True], ids=["room", "window-top"])
def test_the_toolbar_never_covers_the_picked_blocks(editor, top):
    """A8: above the picked blocks or, with no room, below them and the menu."""
    page = editor(box("a", "text", TEXT, y=60), box("b", "text", TEXT, z=2, y=90))
    pick(page, "a", "b")
    if top:
        # The blocks scrolled up to the window's top edge: no room above them.
        page.locator(".desk").evaluate(
            "(d, a) => d.scrollBy(0, a.getBoundingClientRect().top - 4)",
            page.locator('[data-id="a"]').element_handle(),
        )
        assert rect(page, "a")["top"] < 40
    right(page, "b")
    expect(mini(page)).to_be_visible()
    row = rect(page, "toolbar")
    for name in ("a", "b", "menu"):
        assert apart(row, rect(page, name)), name
    assert row["left"] >= 0 and row["right"] <= page.viewport_size["width"]


KINDS = ["text", "shape", "line", "image", "table", "ruling", "maths", "group"]


@pytest.mark.parametrize("kind", KINDS)
def test_each_button_is_enabled_for_what_the_panel_turns(editor, kind):
    """I1: rotate is off for a table and a line on its own, align is on, the brush has a source."""
    client = user()
    if kind == "group":
        blocks = [box("a", "shape", RECT, z=1, **GROUP), box("b", "shape", RECT, z=2, **GROUP)]
    elif kind == "line":
        blocks = [box("a", "shape", LINE)]
    elif kind == "image":
        blocks = [box("a", "image", props(client, "image"))]
    else:
        blocks = [box("a", kind, props(client, kind))]
    page = editor(*blocks, client=client)
    right(page, "a")
    turns = kind in ("text", "shape", "image", "ruling", "maths", "group")
    for name in ("Linksdrehung 90°", "Rechtsdrehung 90°"):
        if turns:
            expect(tool(page, name)).to_be_enabled()
        else:
            expect(tool(page, name)).to_be_disabled()
    # The picked block is the source of the format, so the brush is on for every kind.
    for name in MINI[2:]:
        expect(tool(page, name)).to_be_enabled()


def test_several_blocks_turn_each_and_align_keeps_the_picked(editor):
    """I2"""
    page = editor(*texts(*"ab"))
    pick(page, "a", "b")
    right(page, "b")
    tool(page, "Rechtsdrehung 90°").click()
    expect(page.get_by_role("button", name="Rückgängig")).to_be_enabled()
    assert angle(page, "a") == 90 and angle(page, "b") == 90
    right(page, "b")
    tool(page, "Oben").click()
    expect(menu(page)).to_have_count(0)
    expect(page.get_by_role("button", name="Rückgängig")).to_be_enabled()
    expect_picked(page, "a", "b")


def test_the_arrows_walk_the_menu_entries_only(editor):
    """I3"""
    page = editor(*texts(*"ab"))
    right(page, "a")
    expect(page.get_by_role("menuitem", name="Ausschneiden", exact=True)).to_be_focused()
    for _ in range(25):
        page.keyboard.press("ArrowDown")
        assert not page.evaluate("!!document.activeElement.closest('.mini')")


def test_escape_shuts_the_menu_and_its_toolbar(editor):
    """I3"""
    page = editor(*texts("a"))
    right(page, "a")
    page.keyboard.press("Escape")
    expect(menu(page)).to_have_count(0)
    expect(mini(page)).to_have_count(0)


@pytest.mark.parametrize("opened", ["corner", "thumb"])
def test_the_page_and_empty_menus_have_no_toolbar(editor, opened):
    """I4"""
    page = editor(*texts("a"), pages=[{"blocks": texts("b")}], theme="")
    if opened == "thumb":
        right_thumb(page, 1)
    else:
        corner(page)
    expect(menu(page)).to_be_visible()
    expect(mini(page)).to_have_count(0)


def test_format_uebertragen_in_the_toolbar_paints_the_next_block_once(editor):
    """A6: one stroke, as one click on the bar's brush."""
    client = user()
    page = editor(
        box("a", "shape", {**RECT, "fill": "#00ff00"}),
        box("b", "shape", RECT, z=2, x=120),
        box("c", "shape", RECT, z=3, y=150),
        client=client,
    )
    right(page, "a")
    tool(page, "Format übertragen").click()
    expect(menu(page)).to_have_count(0)
    expect_brush(page, True)
    at(page, "b").click()
    expect_brush(page, False)
    at(page, "c").click()
    now = held(page, client)
    assert now["b"]["fill"] == "#00ff00"
    assert now["c"].get("fill") == RECT.get("fill")
    undo = page.get_by_role("button", name="Rückgängig")
    undo.click()
    assert held(page, client)["b"].get("fill") == RECT.get("fill")


def test_on_a_block_of_another_page_the_toolbar_keeps_clear_of_it_and_the_menu(editor):
    """A8, review"""
    page = three(editor)
    pick(page, "a")
    right(page, "c")
    expect_picked(page, "c")
    row = rect(page, "toolbar")
    for name in ("c", "menu"):
        assert apart(row, rect(page, name)), name


def test_on_a_block_low_in_the_window_the_toolbar_keeps_clear_of_the_menu(editor):
    """A8, review: the menu moves up into the window, over the room above the block."""
    page = editor(box("a", "text", TEXT, y=250))
    page.locator(".desk").evaluate(
        "(d, a) => d.scrollBy(0, a.getBoundingClientRect().bottom - innerHeight + 10)",
        page.locator('[data-id="a"]').element_handle(),
    )
    right(page, "a")
    row = rect(page, "toolbar")
    for name in ("a", "menu"):
        assert apart(row, rect(page, name)), name


def test_a_group_with_a_locked_block_does_not_turn(editor):
    """I1, review: as the panel, whose turn buttons are off then."""
    page = editor(
        box("fest", "text", TEXT, locked=True, group=["g"]),
        box("frei", "text", TEXT, z=2, y=120, group=["g"]),
    )
    right(page, "frei")
    expect_picked(page, "fest", "frei")
    expect(tool(page, "Rechtsdrehung 90°")).to_be_disabled()
    # The group stays as it is, as in the panel: nothing of it lines up either.
    expect(tool(page, "Links")).to_be_disabled()
