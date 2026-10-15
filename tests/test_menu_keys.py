"""The keys open the menu of the selection: Shift+F10 and the Menu key, as in PowerPoint."""

from playwright.sync_api import expect
from test_menu import item, menu, right, texts
from ui import TEXT, at, box, expect_picked, pick


def watch(page):
    """Keeps each contextmenu event's defaultPrevented, read after the bubble."""
    page.evaluate(
        "window.cm = []; addEventListener('contextmenu', (e) => window.cm.push(e.defaultPrevented))"
    )


def kept(page):
    return page.evaluate("window.cm")


def test_shift_f10_opens_the_menu_at_the_selection(editor):
    """I1"""
    page = editor(*texts(*"ab"))
    pick(page, "b")
    page.keyboard.press("Shift+F10")
    expect(menu(page)).to_be_visible()
    expect(menu(page).locator("button:enabled").first).to_be_focused()
    b = at(page, "b").bounding_box()
    m = menu(page).bounding_box()
    assert b["x"] <= m["x"] <= b["x"] + b["width"]
    assert b["y"] <= m["y"] <= b["y"] + b["height"]


def test_the_menu_key_opens_the_menu(editor):
    """I2"""
    page = editor(*texts(*"ab"))
    pick(page, "b")
    page.keyboard.press("ContextMenu")
    expect(menu(page)).to_be_visible()
    expect(menu(page).locator("button:enabled").first).to_be_focused()


def test_arrows_enter_and_escape_work_in_the_keys_menu(editor):
    """I3"""
    page = editor(*texts(*"ab"))
    pick(page, "b")
    page.keyboard.press("Shift+F10")
    expect(menu(page)).to_be_visible()
    first = menu(page).locator("button:enabled").first
    expect(first).to_be_focused()
    page.keyboard.press("ArrowDown")
    expect(first).not_to_be_focused()
    page.keyboard.press("ArrowUp")
    expect(first).to_be_focused()
    item(page, "Löschen").focus()
    page.keyboard.press("Enter")
    expect(menu(page)).to_have_count(0)
    expect(at(page, "b")).to_have_count(0)
    expect(at(page, "a")).to_have_count(1)
    page.keyboard.press("Shift+F10")
    expect(menu(page)).to_be_visible()
    page.keyboard.press("Escape")
    expect(menu(page)).to_have_count(0)


def test_the_browsers_menu_does_not_come_up_with_the_keys(editor):
    """I4: the probe found whether Playwright's key makes a contextmenu event at all."""
    page = editor(*texts(*"ab"))
    pick(page, "b")
    watch(page)
    page.keyboard.press("Shift+F10")
    expect(menu(page)).to_be_visible()
    page.keyboard.press("Escape")
    page.keyboard.press("ContextMenu")
    expect(menu(page)).to_be_visible()
    assert all(kept(page))


def test_with_a_text_open_the_keys_leave_the_browsers_menu(editor):
    """I5"""
    page = editor(*texts(*"ab"))
    at(page, "b").dblclick()
    expect(page.locator(".ProseMirror")).to_be_focused()
    watch(page)
    page.keyboard.press("Shift+F10")
    expect(menu(page)).to_have_count(0)
    assert not any(kept(page))


def test_escape_keeps_the_selection_and_the_sheet_keeps_the_keys(editor):
    """I6"""
    page = editor(*texts(*"ab"))
    pick(page, "b")
    page.keyboard.press("Shift+F10")
    expect(menu(page)).to_be_visible()
    page.keyboard.press("Escape")
    expect(menu(page)).to_have_count(0)
    expect_picked(page, "b")
    page.keyboard.press("Delete")
    expect(at(page, "b")).to_have_count(0)


def test_loschen_from_the_keys_is_one_undo_step(editor):
    """I7"""
    page = editor(*texts(*"ab"))
    pick(page, "b")
    page.keyboard.press("Shift+F10")
    item(page, "Löschen").focus()
    page.keyboard.press("Enter")
    expect(at(page, "b")).to_have_count(0)
    page.keyboard.press("Control+z")
    expect(at(page, "b")).to_have_count(1)
    expect(page.get_by_role("button", name="Rückgängig", exact=True)).to_be_disabled()


def test_nothing_picked_opens_the_menu_with_einfugen_enabled(editor):
    """I8"""
    page = editor(*texts(*"ab"))
    page.locator(".sheet").first.click(position={"x": 5, "y": 5})
    page.keyboard.press("Shift+F10")
    expect(menu(page)).to_be_visible()
    expect(item(page, "Einfügen")).to_be_enabled()


def test_two_picked_blocks_open_one_menu(editor):
    """I9a"""
    page = editor(*texts(*"ab"))
    pick(page, "a", "b")
    page.keyboard.press("Shift+F10")
    expect(menu(page)).to_have_count(1)
    expect(menu(page)).to_be_visible()


def test_a_locked_block_gets_the_menu_with_loschen_disabled(editor):
    """I9b"""
    page = editor(box("fest", "text", TEXT, locked=True))
    pick(page, "fest")
    page.keyboard.press("Shift+F10")
    expect(menu(page)).to_be_visible()
    expect(item(page, "Löschen")).to_be_disabled()


def test_the_menu_stays_inside_the_window_near_the_bottom_right(editor):
    """I10"""
    page = editor(box("a", "text", TEXT, z=1, x=170, y=270))
    pick(page, "a")
    page.keyboard.press("Shift+F10")
    expect(menu(page)).to_be_visible()
    m = menu(page).bounding_box()
    size = page.viewport_size
    assert m["x"] >= 0 and m["y"] >= 0
    assert m["x"] + m["width"] <= size["width"]
    assert m["y"] + m["height"] <= size["height"]


def test_a_focused_bar_button_keeps_the_key(editor):
    """I11"""
    page = editor(*texts(*"ab"))
    pick(page, "b")
    page.keyboard.press("Delete")
    # Rückgängig is a button only once a step can be taken back: a disabled one takes no focus.
    undo = page.get_by_label("Rückgängig", exact=True)
    expect(undo).to_be_enabled()
    undo.focus()
    expect(undo).to_be_focused()
    page.keyboard.press("Shift+F10")
    expect(menu(page)).to_have_count(0)


def test_ctrl_shift_f10_opens_no_menu(editor):
    """Extra 1: Ctrl with Shift+F10 is not the menu's key."""
    page = editor(*texts(*"ab"))
    pick(page, "b")
    page.keyboard.press("Control+Shift+F10")
    expect(menu(page)).to_have_count(0)


def test_the_menu_opens_again_after_escape(editor):
    """Extra 2: a second open after Escape gives the menu back at the selection."""
    page = editor(*texts(*"ab"))
    pick(page, "a")
    page.keyboard.press("Shift+F10")
    expect(menu(page)).to_be_visible()
    page.keyboard.press("Escape")
    expect(menu(page)).to_have_count(0)
    page.keyboard.press("ContextMenu")
    expect(menu(page)).to_be_visible()
    expect(menu(page).locator("button:enabled").first).to_be_focused()


def test_shift_f10_at_once_after_escape_opens_the_menu_again(editor):
    """#626: no wait between Escape and the key."""
    page = editor(*texts(*"ab"))
    pick(page, "a")
    page.keyboard.press("Shift+F10")
    expect(menu(page)).to_be_visible()
    page.keyboard.press("Escape")
    page.keyboard.press("Shift+F10")
    expect(menu(page)).to_be_visible()
    # A late close of the first menu would shut this one.
    page.wait_for_timeout(300)
    expect(menu(page)).to_be_visible()


def test_a_right_click_menu_shut_by_escape_comes_back_by_the_menu_key(editor):
    page = editor(*texts(*"ab"))
    pick(page, "a")
    right(page, "a")
    page.keyboard.press("Escape")
    page.keyboard.press("ContextMenu")
    expect(menu(page)).to_be_visible()
    expect(menu(page).locator("button:enabled").first).to_be_focused()


def test_escape_then_delete_at_once_deletes_the_picked_block(editor):
    page = editor(*texts(*"ab"))
    pick(page, "b")
    page.keyboard.press("Shift+F10")
    expect(menu(page)).to_be_visible()
    page.keyboard.press("Escape")
    page.keyboard.press("Delete")
    expect(at(page, "b")).to_have_count(0)
    expect(at(page, "a")).to_have_count(1)


def test_an_item_run_by_enter_then_the_key_at_once_opens_the_menu(editor):
    page = editor(*texts(*"abc"))
    pick(page, "b")
    page.keyboard.press("Shift+F10")
    item(page, "Löschen").focus()
    page.keyboard.press("Enter")
    page.keyboard.press("ContextMenu")
    expect(menu(page)).to_be_visible()
    expect(at(page, "b")).to_have_count(0)
