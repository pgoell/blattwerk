"""The right click's menu: on a block, on the empty page and on a page's thumbnail."""

import pytest
from playwright.sync_api import expect
from test_clipboard import REFUSE, STAR
from test_order import boxes, expect_stack
from test_pages import expect_in_use, expect_order, three
from ui import (
    BROWSER,
    FIELD,
    LINE,
    RECT,
    RULING,
    TABLE,
    TEXT,
    apart,
    at,
    box,
    centre,
    copy_picture,
    expect_picked,
    finger,
    hold_drag,
    jitter,
    maths,
    order,
    outlast,
    pick,
    picture,
    saved,
    thumb,
    upload,
    user,
)

GROUP = {"group": ["g"]}
KINDS = ["text", "shape", "line", "image", "symbol", "table", "ruling", "name", "points", "maths"]
# The blocks a held finger is tried on.
HELD = ["text", "shape", "line", "image", "table", "ruling", "maths", "group"]


def menu(page):
    return page.get_by_role("menu")


def item(page, name):
    return page.get_by_role("menuitem", name=name, exact=True)


def watch(page):
    """Keeps the next right click's event, to ask it later whether the page kept it."""
    page.evaluate("addEventListener('contextmenu', (e) => (window.asked = e), true)")


def kept(page):
    return page.evaluate("window.asked.defaultPrevented")


def right(page, name):
    """A right click on the block: by its place, for a selection's frame may lie over it."""
    at(page, name).scroll_into_view_if_needed()
    page.mouse.click(*centre(at(page, name)), button="right")
    expect(menu(page)).to_be_visible()


def corner(page):
    """A right click on the empty corner of the first page."""
    page.locator(".sheet").first.click(position={"x": 5, "y": 5}, button="right")
    expect(menu(page)).to_be_visible()


def run(page, name):
    item(page, name).click()
    expect(menu(page)).to_have_count(0)


def texts(*names):
    return [box(name, "text", TEXT, z=i + 1) for i, name in enumerate(names)]


def left(page, name):
    return at(page, name).evaluate("el => getComputedStyle(el).left")


def nudged(page, name):
    """Moves the block by a key: a change of the sheet to undo. Gives where it was."""
    pick(page, name)
    before = left(page, name)
    page.keyboard.press("ArrowRight")
    expect(at(page, name)).not_to_have_css("left", before)
    return before


def props(client, kind):
    made = {
        "text": TEXT,
        "shape": RECT,
        "line": LINE,
        "symbol": STAR,
        "table": TABLE,
        "ruling": RULING,
        "name": {},
        "points": {"max": 10},
    }
    if kind == "image":
        return picture(upload(client))["props"]
    return maths(client) if kind == "maths" else made[kind]


@pytest.mark.parametrize("kind", KINDS)
def test_a_right_click_on_a_block_opens_the_editors_menu(editor, kind):
    """A1"""
    client = user()
    page = editor(box("a", "shape" if kind == "line" else kind, props(client, kind)), client=client)
    watch(page)
    right(page, "a")
    assert kept(page)
    expect(item(page, "Ausschneiden")).to_be_enabled()
    expect_picked(page, "a")


def test_a_right_click_on_a_group_opens_the_editors_menu(editor):
    """A1"""
    page = editor(*boxes(*"abc", grouped="ab"))
    watch(page)
    right(page, "a")
    assert kept(page)
    expect_picked(page, "a", "b")
    expect(item(page, "Gruppierung aufheben")).to_be_enabled()


def test_ausschneiden_takes_the_block_away_and_einfuegen_brings_it_back(editor):
    """A2, A4 on the empty page"""
    page = editor(*texts(*"ab"))
    right(page, "a")
    run(page, "Ausschneiden")
    expect(page.locator(".block[data-id]")).to_have_count(1)
    assert order(page) == [["b"]]
    corner(page)
    run(page, "Einfügen")
    expect(page.locator(".block[data-id]")).to_have_count(2)


def test_kopieren_keeps_the_block_and_einfuegen_on_a_block_adds_a_copy(editor):
    """A3, A4 on a block"""
    page = editor(*texts(*"ab"))
    right(page, "a")
    run(page, "Kopieren")
    expect(page.locator(".block[data-id]")).to_have_count(2)
    right(page, "b")
    run(page, "Einfügen")
    expect(page.locator(".block[data-id]")).to_have_count(3)
    expect(page.locator(".block.sel")).to_have_count(1)
    expect(at(page, "b")).not_to_have_class("block sel")


@pytest.mark.webkit_xfail(204, "headless WebKit on Linux keeps no picture on the clipboard")
def test_einfuegen_pastes_a_picture_from_another_app(editor):
    """A4"""
    page = editor(*texts("a"))
    copy_picture(page)
    corner(page)
    run(page, "Einfügen")
    expect(page.locator(".block .picture img")).to_have_js_property("naturalWidth", 3)


@pytest.mark.parametrize("entry", ["Kopieren", "Ausschneiden"])
def test_a_copy_the_browser_lets_no_one_write_still_wins_over_an_older_picture(editor, entry):
    """#174"""
    client = user()
    page = editor(*texts("a"), client=client)
    copy_picture(page)
    page.evaluate(REFUSE)
    right(page, "a")
    run(page, entry)
    count = 2 if entry == "Kopieren" else 1
    expect(page.locator(".block[data-id]")).to_have_count(count - 1)
    corner(page)
    run(page, "Einfügen")
    expect(page.locator(".block[data-id]")).to_have_count(count)
    assert [b["type"] for b in saved(page, client)] == ["text"] * count


def test_duplizieren_adds_a_copy_and_selects_it(editor):
    """A5"""
    page = editor(*texts(*"ab"))
    right(page, "a")
    run(page, "Duplizieren")
    expect(page.locator(".block[data-id]")).to_have_count(3)
    expect(page.locator(".block.sel")).to_have_count(1)
    expect(at(page, "a")).not_to_have_class("block sel")


def test_loeschen_takes_the_block_away(editor):
    """A6"""
    client = user()
    page = editor(*texts(*"ab"), client=client)
    right(page, "b")
    run(page, "Löschen")
    expect(page.locator(".block[data-id]")).to_have_count(1)
    assert [b["id"] for b in saved(page, client)] == ["a"]


def test_sperren_locks_the_block_and_entsperren_frees_it(editor):
    """A7"""
    client = user()
    page = editor(*texts("a"), client=client)
    right(page, "a")
    expect(item(page, "Entsperren")).to_have_count(0)
    run(page, "Sperren")
    assert saved(page, client)[0]["locked"]
    right(page, "a")
    expect(item(page, "Sperren")).to_have_count(0)
    run(page, "Entsperren")
    assert not saved(page, client)[0]["locked"]


def test_gruppieren_joins_the_selection_and_gruppierung_aufheben_splits_it(editor):
    """A8"""
    client = user()
    page = editor(*texts(*"abc"), client=client)
    pick(page, "a", "b")
    right(page, "a")
    run(page, "Gruppieren")
    groups = [b.get("group") for b in saved(page, client)]
    assert groups[0] == groups[1] != None  # noqa: E711
    assert groups[2] is None
    # One click on a part now picks the whole group.
    pick(page, "c")
    at(page, "a").click()
    expect_picked(page, "a", "b")
    right(page, "b")
    run(page, "Gruppierung aufheben")
    assert [b.get("group") for b in saved(page, client)] == [None] * 3


@pytest.mark.parametrize(
    ("name", "entry", "after"),
    [
        ("a", "In den Vordergrund", "bcda"),
        ("a", "Eine Ebene nach vorn", "bacd"),
        ("d", "Eine Ebene nach hinten", "abdc"),
        ("d", "In den Hintergrund", "dabc"),
    ],
)
def test_the_layer_entries_move_the_block_in_the_stack(editor, name, entry, after):
    """A9"""
    page = editor(*boxes(*"abcd"))
    expect_stack(page, "abcd")
    right(page, name)
    run(page, entry)
    expect_stack(page, after)


def right_thumb(page, n):
    thumb(page, n).click(button="right")
    expect(menu(page)).to_be_visible()


def test_a_right_click_on_a_thumbnail_opens_the_pages_menu(editor):
    """A10"""
    page = three(editor)
    watch(page)
    right_thumb(page, 1)
    assert kept(page)
    expect(page.get_by_role("menuitem")).to_have_text(
        ["Neue Seite", "Seite duplizieren", "Seite löschen"]
    )


def test_neue_seite_comes_after_the_thumbnails_page(editor):
    """A10"""
    page = three(editor)
    right_thumb(page, 1)
    run(page, "Neue Seite")
    expect(page.locator(".sheet[data-page]")).to_have_count(4)
    assert order(page) == [["a"], ["b"], [], ["c"]]
    expect_in_use(page, 2)


def test_seite_duplizieren_copies_the_thumbnails_page(editor):
    """A10"""
    page = three(editor)
    right_thumb(page, 1)
    run(page, "Seite duplizieren")
    expect_order(page, "ab+c")


def test_seite_loeschen_takes_the_thumbnails_page_away(editor):
    """A10"""
    page = three(editor)
    right_thumb(page, 2)
    run(page, "Seite löschen")
    expect_order(page, "ab")
    right_thumb(page, 0)
    run(page, "Seite löschen")
    expect_order(page, "b")


def test_a_right_click_on_an_unselected_block_selects_it_alone(editor):
    """I1"""
    page = editor(*texts(*"abc"))
    pick(page, "a", "b")
    right(page, "c")
    expect_picked(page, "c")


def test_a_right_click_on_an_unselected_group_selects_the_whole_group(editor):
    """I1"""
    page = editor(*boxes(*"abc", grouped="bc"))
    pick(page, "a")
    right(page, "b")
    expect_picked(page, "b", "c")


def test_a_right_click_on_a_block_of_the_selection_keeps_the_selection(editor):
    """I1"""
    page = editor(*boxes(*"abcd", grouped="cd"))
    pick(page, "a", "b")
    right(page, "a")
    expect_picked(page, "a", "b")
    page.keyboard.press("Escape")
    # A picked group stays whole: the right click picks no block out of it.
    at(page, "c").click()
    expect_picked(page, "c", "d")
    right(page, "c")
    expect_picked(page, "c", "d")
    page.keyboard.press("Escape")
    expect(menu(page)).to_have_count(0)
    expect_picked(page, "c", "d")


def test_a_right_click_on_the_empty_page_selects_nothing(editor):
    """I1"""
    page = editor(*texts(*"ab"))
    pick(page, "a", "b")
    corner(page)
    expect_picked(page)


def test_a_right_click_on_a_block_of_another_page_puts_that_page_in_use(editor):
    """I1"""
    page = three(editor)
    pick(page, "a")
    right(page, "c")
    expect_in_use(page, 2)
    expect_picked(page, "c")


def test_escape_closes_the_menu_and_changes_nothing(editor):
    """I2"""
    page = editor(*texts(*"ab"))
    before = nudged(page, "a")
    right(page, "a")
    page.keyboard.press("Escape")
    expect(menu(page)).to_have_count(0)
    expect_picked(page, "a")
    # The nudge is still the last change.
    page.keyboard.press("Control+z")
    expect(at(page, "a")).to_have_css("left", before)
    expect(page.locator(".block[data-id]")).to_have_count(2)


def test_a_press_beside_the_menu_closes_it_and_changes_nothing(editor):
    """I2"""
    page = editor(*texts(*"ab"))
    before = nudged(page, "b")
    right(page, "b")
    # On another block, above the menu: the press is the menu's, and picks nothing.
    page.mouse.click(*centre(at(page, "a")))
    expect(menu(page)).to_have_count(0)
    expect_picked(page, "b")
    page.keyboard.press("Control+z")
    expect(at(page, "b")).to_have_css("left", before)


def test_a_right_click_elsewhere_moves_the_menu_there(editor):
    """I2"""
    page = editor(*texts(*"ab"), pages=[{"blocks": [box("c", "text", TEXT)]}], theme="")
    right(page, "b")
    first = menu(page).bounding_box()
    watch(page)
    # The block above the menu.
    x, y = centre(at(page, "a"))
    page.mouse.click(x, y, button="right")
    expect_picked(page, "a")
    expect(menu(page)).to_have_count(1)
    assert kept(page)
    moved = menu(page).bounding_box()
    assert moved["y"] < first["y"]
    assert abs(moved["x"] - x) < 1
    assert abs(moved["y"] - y) < 1
    # From the desk to a thumbnail.
    thumb(page, 1).click(button="right", force=True)
    expect(item(page, "Seite löschen")).to_be_visible()
    expect(menu(page)).to_have_count(1)
    expect_in_use(page, 1)
    # Beside the desk and the thumbnails there is no menu.
    page.locator("header input[aria-label=Titel]").click(button="right", force=True)
    expect(menu(page)).to_have_count(0)


def test_the_arrows_walk_the_enabled_entries_and_enter_runs_one(editor):
    """I3"""
    page = editor(*texts(*"ab"))
    right(page, "a")
    expect(item(page, "Ausschneiden")).to_be_focused()
    page.keyboard.press("ArrowUp")
    expect(item(page, "In den Hintergrund")).to_be_focused()
    page.keyboard.press("ArrowDown")
    expect(item(page, "Ausschneiden")).to_be_focused()
    for name in ("Kopieren", "Einfügen", "Duplizieren", "Löschen", "Sperren"):
        page.keyboard.press("ArrowDown")
        expect(item(page, name)).to_be_focused()
    # Neither Gruppieren nor Gruppierung aufheben can do anything for one block.
    page.keyboard.press("ArrowDown")
    expect(item(page, "In den Vordergrund")).to_be_focused()
    page.keyboard.press("ArrowUp")
    page.keyboard.press("ArrowUp")
    expect(item(page, "Löschen")).to_be_focused()
    page.keyboard.press("Enter")
    expect(menu(page)).to_have_count(0)
    expect(page.locator(".block[data-id]")).to_have_count(1)
    assert order(page) == [["b"]]


@pytest.mark.parametrize("keys", ["Delete", "Backspace", "Control+x", "Control+d", "ArrowRight"])
def test_the_sheets_keys_do_not_reach_it_while_the_menu_is_open(editor, keys):
    """I3"""
    page = editor(*texts(*"ab"))
    right(page, "a")
    before = left(page, "a")
    page.keyboard.press(keys)
    page.keyboard.press("Escape")
    expect(menu(page)).to_have_count(0)
    # Nothing to undo: the key made no step.
    expect(page.get_by_role("button", name="Rückgängig")).to_be_disabled()
    assert order(page) == [["a", "b"]]
    assert left(page, "a") == before


def test_on_the_empty_page_only_einfuegen_can_run(editor):
    """I4"""
    page = editor(*texts(*"ab"))
    corner(page)
    entries = page.get_by_role("menuitem")
    expect(entries).to_have_count(12)
    expect(item(page, "Einfügen")).to_be_enabled()
    expect(item(page, "Einfügen")).to_be_focused()
    expect(page.locator("[role=menuitem]:enabled")).to_have_count(1)


def test_gruppieren_and_gruppierung_aufheben_follow_their_buttons(editor):
    """I4"""
    page = editor(*boxes(*"abcd", grouped="cd"))
    right(page, "a")
    for name in ("Gruppieren", "Gruppierung aufheben"):
        expect(item(page, name)).to_be_disabled()
        expect(page.get_by_role("button", name=name, exact=True)).to_be_disabled()
    page.keyboard.press("Escape")
    pick(page, "a", "b")
    right(page, "a")
    expect(item(page, "Gruppieren")).to_be_enabled()
    expect(item(page, "Gruppierung aufheben")).to_be_disabled()
    page.keyboard.press("Escape")
    right(page, "c")
    expect(item(page, "Gruppieren")).to_be_disabled()
    expect(item(page, "Gruppierung aufheben")).to_be_enabled()


def test_seite_loeschen_is_off_with_one_page(editor):
    """I4"""
    page = editor(*texts("a"), theme="")
    right_thumb(page, 0)
    expect(item(page, "Seite löschen")).to_be_disabled()
    expect(item(page, "Neue Seite")).to_be_enabled()
    expect(item(page, "Seite duplizieren")).to_be_enabled()


def expect_the_browsers(page, locator):
    watch(page)
    locator.click(button="right")
    assert not kept(page)
    expect(menu(page)).to_have_count(0)


def test_an_open_text_field_keeps_the_browsers_menu(editor):
    """I5"""
    page = editor(*texts("a"))
    pick(page, "a")
    page.keyboard.press("Enter")
    expect(page.locator(FIELD)).to_be_focused()
    expect_the_browsers(page, page.locator(FIELD))
    expect(page.locator(FIELD)).to_be_focused()


def test_a_table_cell_keeps_the_browsers_menu(editor):
    """I5"""
    page = editor(box("a", "table", TABLE))
    pick(page, "a")
    page.keyboard.press("Enter")
    cell = page.locator(".block.sel textarea").first
    expect(cell).to_be_visible()
    expect_the_browsers(page, cell)


def test_an_input_keeps_the_browsers_menu(editor):
    """I5"""
    page = editor(*texts("a"))
    expect_the_browsers(page, page.get_by_label("Titel"))


@pytest.mark.parametrize("entry", ["Löschen", "Duplizieren", "Ausschneiden", "Sperren"])
def test_an_entrys_change_is_one_undo_step_right_after_the_menu(editor, entry):
    """I6"""
    page = editor(*texts(*"ab"))
    before = nudged(page, "a")
    right(page, "a")
    run(page, entry)
    left_over = {"Duplizieren": 3, "Sperren": 2}.get(entry, 1)
    expect(page.locator(".block[data-id]")).to_have_count(left_over)
    expect(page.get_by_role("button", name="Wiederholen")).to_be_disabled()
    # The keys are the sheet's again: one undo takes the entry's change back, the next the nudge.
    page.keyboard.press("Control+z")
    expect(page.locator(".block[data-id]")).to_have_count(2)
    expect(page.get_by_role("button", name="Wiederholen")).to_be_enabled()
    expect(at(page, "a")).not_to_have_css("left", before)
    page.keyboard.press("Control+z")
    expect(at(page, "a")).to_have_css("left", before)
    expect(page.get_by_role("button", name="Rückgängig")).to_be_disabled()


def test_a_page_entrys_change_is_one_undo_step(editor):
    """I6"""
    page = three(editor)
    right_thumb(page, 1)
    run(page, "Seite löschen")
    expect_order(page, "ac")
    page.keyboard.press("Control+z")
    expect_order(page, "abc")
    expect(page.get_by_role("button", name="Rückgängig")).to_be_disabled()


def test_undo_works_after_a_page_entry_though_the_title_had_the_focus(editor):
    """I6"""
    page = three(editor)
    page.get_by_label("Titel").click()
    right_thumb(page, 1)
    run(page, "Seite löschen")
    expect_order(page, "ac")
    # The menu must not hand the focus back to the title, which keeps the keys to itself.
    page.keyboard.press("Control+z")
    expect_order(page, "abc")


def test_a_menu_higher_than_the_window_scrolls(editor):
    """I7"""
    page = editor(*texts("a"))
    page.set_viewport_size({"width": 900, "height": 320})
    right(page, "a")
    box = menu(page).bounding_box()
    assert box["y"] >= 0 and box["y"] + box["height"] <= 320
    item(page, "In den Hintergrund").click()
    expect(menu(page)).to_be_hidden()


def test_the_menu_stays_inside_the_window(editor):
    """I7"""
    page = editor(*texts("a"))
    page.set_viewport_size({"width": 900, "height": 500})
    desk = page.locator(".desk").bounding_box()
    # The desk's scroll bars lie at its very edge.
    x, y = desk["x"] + desk["width"] - 30, desk["y"] + desk["height"] - 30
    page.mouse.click(x, y, button="right")
    expect(menu(page)).to_be_visible()
    shown = menu(page).bounding_box()
    assert shown["x"] + shown["width"] <= 900
    assert shown["y"] + shown["height"] <= 500
    assert shown["x"] >= 0
    assert shown["y"] >= 0
    # It did move: it would not fit below and right of the click.
    assert shown["x"] < x
    assert shown["y"] < y


def test_a_right_click_on_a_thumbnail_puts_its_page_in_use(editor):
    """I8"""
    page = three(editor)
    pick(page, "a")
    right_thumb(page, 2)
    expect_in_use(page, 2)
    expect_picked(page)
    page.keyboard.press("Escape")
    expect(menu(page)).to_have_count(0)
    expect_in_use(page, 2)
    expect_order(page, "abc")


def test_a_held_finger_gets_no_menu_of_the_editors(editor):
    """Touch stays as it was: the browser's menu is kept away and the editor's stays shut."""
    page = editor(*texts("a"), touch=True)
    at(page, "a").tap()
    expect_picked(page, "a")
    watch(page)
    at(page, "a").dispatch_event("contextmenu", {"bubbles": True, "cancelable": True})
    assert kept(page)
    expect(menu(page)).to_have_count(0)


def several(page):
    return page.get_by_label("Mehrere", exact=True)


@pytest.mark.parametrize("kind", HELD)
def test_a_jittering_finger_held_on_a_block_starts_selecting_several(editor, kind):
    """B3"""
    client = user()
    if kind == "group":
        blocks = boxes(*"abc", grouped="ab")
    else:
        blocks = [box("a", "shape" if kind == "line" else kind, props(client, kind))]
    page = editor(*blocks, client=client, touch=True)
    expect(several(page)).to_have_attribute("aria-pressed", "false")
    # The block is selected with the finger still down: a tap would select it on the way up.
    by = ((3, 0), (0, 4), (-6, -7))
    hold_drag(page, at(page, "a"), centre(at(page, "a")), by=by, shows="sel")
    expect(several(page)).to_have_attribute("aria-pressed", "true")
    expect_picked(page, *("ab" if kind == "group" else "a"))


def spot(page, name):
    """Where the block lies on its page, as its own style says."""
    return at(page, name).evaluate("el => [el.style.left, el.style.top]")


@pytest.mark.parametrize("kind", [*HELD, "several"])
def test_a_jittering_finger_held_on_a_selected_block_moves_no_block(editor, kind):
    """#178"""
    client = user()
    if kind in ("group", "several"):
        # Apart: a tap reaches each block, and no block or middle of the page lies near enough to
        # snap to. A snap moves the blocks before the finger has left (#261).
        blocks = apart(*boxes(*"abc", grouped="ab" if kind == "group" else ""))
    else:
        blocks = [box("a", "shape" if kind == "line" else kind, props(client, kind))]
    page = editor(*blocks, client=client, touch=True)
    names = "ab" if len(blocks) > 1 else "a"
    if kind == "several":
        several(page).tap()
    for name in names if kind == "several" else "a":
        at(page, name).tap()
    expect_picked(page, *names)
    before = [spot(page, name) for name in names]
    # A table's middle is the bar between its columns, which drags no block.
    start = centre(at(page, "a").locator("[data-cell]").first if kind == "table" else at(page, "a"))
    with finger(page, start):
        jitter(at(page, "a"), start, (3, 0), (3, 9))
        outlast(page)
        assert [spot(page, name) for name in names] == before
    assert [spot(page, name) for name in names] == before
    expect(page.get_by_role("button", name="Rückgängig")).to_be_disabled()


# Px to the mm of the sheet, by the window.
SCALE = {}
# How far above `a` its neighbour ends, in px: outside the slop, and a snap reaches it from 9 px.
GAP = 13


def beside(editor, client, kind, touch=True):
    """Selects `a`, or `a` and `b`, just below a neighbour to snap to. Gives the page, the selected
    names and where the finger comes down on `a`."""
    if touch not in SCALE:
        # The layout says how large the sheet is, and a snap counts in px: measure, then lay out.
        SCALE[touch] = editor(touch=touch).locator(".sheet").first.bounding_box()["width"] / 210
    y = round(40 + GAP / SCALE[touch], 2)
    neighbour = {**box("c", "shape", RECT, z=3), "y": 20}
    if kind in ("group", "several"):
        # 70 mm apart: a tap reaches each block past the other's handles.
        pair = boxes(*"ab", grouped="ab" if kind == "group" else "")
        mine = [{**b, "y": y + 70 * i} for i, b in enumerate(pair)]
    else:
        mine = [{**box("a", "shape" if kind == "line" else kind, props(client, kind)), "y": y}]
    page = editor(*mine, neighbour, client=client, touch=touch)
    names = "ab"[: len(mine)]
    if kind == "several":
        several(page).tap()
    for name in names if kind == "several" else "a":
        at(page, name).tap()
    expect_picked(page, *names)
    at(page, "a").scroll_into_view_if_needed()
    # A table's middle is the bar between its columns, which drags no block.
    on = at(page, "a").locator("[data-cell]").first if kind == "table" else at(page, "a")
    return page, names, centre(on)


@pytest.mark.parametrize("touch", [True, "landscape"])
@pytest.mark.parametrize("kind", [*HELD, "several"])
def test_a_jittering_finger_held_beside_a_snap_line_moves_no_block(editor, kind, touch):
    """#261"""
    client = user()
    page, names, start = beside(editor, client, kind, touch)
    before = [spot(page, name) for name in names]
    with finger(page, start):
        jitter(at(page, "a"), start, (3, 0), (3, -9))
        outlast(page)
        assert [spot(page, name) for name in names] == before
    assert [spot(page, name) for name in names] == before
    expect(page.get_by_role("button", name="Rückgängig")).to_be_disabled()
    assert saved(page, client)[0]["y"] == round(40 + GAP / SCALE[touch], 2)


@pytest.mark.parametrize("kind", ["shape", "group", "several"])
def test_a_finger_that_leaves_where_it_came_down_snaps_what_it_drags(editor, kind):
    """#261"""
    client = user()
    page, names, start = beside(editor, client, kind)
    with finger(page, start):
        jitter(at(page, "a"), start, (3, -14))
    expect(page.get_by_role("button", name="Rückgängig")).to_be_enabled()
    # Onto the neighbour's lower edge, and the second block by as much.
    assert [b["y"] for b in saved(page, client)[: len(names)]] == [40, 110][: len(names)]


@pytest.mark.parametrize("kind", HELD)
def test_a_finger_that_snaps_before_it_leaves_takes_the_block_along_in_one_step(editor, kind):
    """#268: A6, I6"""
    client = user()
    page, names, start = beside(editor, client, kind)
    # The snap takes hold while the finger has not left, and holds as it leaves: Moveable says so
    # once only, before the block may move.
    with finger(page, start):
        jitter(at(page, "a"), start, (3, -9), (3, -14), (3, -15))
    undo = page.get_by_role("button", name="Rückgängig")
    expect(undo).to_be_enabled()
    # Onto the neighbour's lower edge, and a group's second block by as much.
    assert [b["y"] for b in saved(page, client)[: len(names)]] == [40, 110][: len(names)]
    undo.tap()
    expect(undo).to_be_disabled()
    y = round(40 + GAP / SCALE[True], 2)
    assert [b["y"] for b in saved(page, client)[: len(names)]] == [y, y + 70][: len(names)]


def test_a_finger_that_leaves_where_it_came_down_drags_the_selected_block(editor):
    """#178"""
    page = editor(*texts("a"), touch=True)
    at(page, "a").tap()
    expect_picked(page, "a")
    before, start = spot(page, "a"), centre(at(page, "a"))
    with finger(page, start):
        jitter(at(page, "a"), start, (0, 9), (0, 14))
        far = spot(page, "a")
        assert far[0] == before[0] and far[1] != before[1]
        # Once it drags, the block follows the finger back to where it came down too.
        jitter(at(page, "a"), start, (0, 5))
        assert spot(page, "a") not in (before, far)
    expect(page.get_by_role("button", name="Rückgängig")).to_be_enabled()


# Not strict: it fails in CI in two runs of seven, and here in 2 of 20 cold starts on one busy core.
# No block lies under the finger then. What the page held is in the failure's text.
@pytest.mark.xfail(
    BROWSER == "webkit", strict=False, reason="#225: the tap picks nothing, now and then"
)
def test_a_touch_the_browser_cancels_starts_no_selecting_of_several(editor):
    """#179"""
    page = editor(*texts("a"), touch=True)
    start = centre(at(page, "a"))
    with finger(page, start) as touch:
        touch("touchCancel")
        outlast(page)
        expect(several(page)).to_have_attribute("aria-pressed", "false")
        expect_picked(page)
        # The finger comes down again, and its lift is a tap.
        touch("touchStart", start)
        early = page.evaluate(STATE, list(start))
    try:
        expect_picked(page, "a")
    except AssertionError as e:
        raise AssertionError(f"DIAG {early} {page.evaluate(STATE, list(start))}") from e


STATE = """([x, y]) => ({
    several: document.querySelector('[aria-pressed]')?.outerHTML.slice(0, 160),
    pressed: [...document.querySelectorAll('[aria-pressed=true]')].map((b) => b.ariaLabel),
    block: document.querySelector('.block')?.className,
    hit: document.elementsFromPoint(x, y).map((el) => el.tagName + '.' + el.className).slice(0, 6),
    active: document.activeElement?.tagName + '.' + document.activeElement?.className,
    fingers: !!window.fingers,
    main: document.querySelector('main')?.className,
    dialog: !!document.querySelector('dialog[open]'),
})"""


def test_a_tap_after_a_hold_the_browser_cancelled_selects_one_more(editor):
    """#179"""
    page = editor(*apart(*texts("a", "b")), touch=True)
    start = centre(at(page, "a"))
    with finger(page, start) as touch:
        expect(several(page)).to_have_attribute("aria-pressed", "true")
        touch("touchCancel")
        touch("touchStart", centre(at(page, "b")))
    expect_picked(page, "a", "b")


def test_a_swipe_over_a_block_starts_no_selecting_of_several(editor):
    """I7"""
    page = editor(*texts("a"), touch=True)
    start = centre(at(page, "a"))
    with finger(page, start):
        jitter(at(page, "a"), start, (14, 0))
        outlast(page)
        expect(several(page)).to_have_attribute("aria-pressed", "false")
        expect_picked(page)
