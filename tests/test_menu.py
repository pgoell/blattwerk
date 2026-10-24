"""The right click's menu: on a block, on the empty page and on a page's thumbnail."""

import pytest
from playwright.sync_api import expect
from test_clipboard import REFUSE, STAR
from test_order import boxes, expect_stack
from test_pages import expect_in_use, three
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
    maths,
    order,
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


def several(page):
    return page.get_by_label("Mehrere", exact=True)


def spot(page, name):
    """Where the block lies on its page, as its own style says."""
    return at(page, name).evaluate("el => [el.style.left, el.style.top]")
