"""The right click's menu: on a block, on the empty page and on a page's thumbnail."""

import pytest
from playwright.sync_api import expect
from test_clipboard import STAR
from test_order import boxes, expect_stack
from test_pages import expect_in_use, expect_order, three
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


def test_einfuegen_pastes_a_picture_from_another_app(editor):
    """A4"""
    page = editor(*texts("a"))
    copy_picture(page)
    corner(page)
    run(page, "Einfügen")
    expect(page.locator(".block .picture img")).to_have_js_property("naturalWidth", 3)


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


def test_a_swipe_over_a_block_starts_no_selecting_of_several(editor):
    """I7"""
    page = editor(*texts("a"), touch=True)
    start = centre(at(page, "a"))
    with finger(page, start):
        jitter(at(page, "a"), start, (14, 0))
        outlast(page)
        expect(several(page)).to_have_attribute("aria-pressed", "false")
        expect_picked(page)
