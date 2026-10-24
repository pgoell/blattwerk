"""The menu on a page thumbnail: a new page, a copy, delete, and undo of that change.

The helpers live in test_menu.py.
"""

import re

from playwright.sync_api import expect
from test_menu import (
    item,
    kept,
    menu,
    right_thumb,
    run,
    texts,
    watch,
)
from test_pages import expect_in_use, expect_order, three
from test_pages_many import expect_chosen, pick_many
from ui import (
    centre,
    expect_picked,
    order,
    pick,
    thumb,
)


def ctrl_click_as_main_button(page, n):
    """Ctrl+click as Chrome on a Mac can send it.

    The press is the main button, so the thumbnail starts a drag, and contextmenu follows
    while that button is still down. Linux Chromium does not fire that event for a Ctrl+left
    click. Playwright's dispatch_event builds a plain Event for contextmenu, so this sends a
    MouseEvent, which is what that Mac press carries.
    """
    el = thumb(page, n)
    x, y = centre(el)
    page.mouse.move(x, y)
    page.keyboard.down("Control")
    page.mouse.down()
    el.evaluate(
        """(el, at) => el.dispatchEvent(new MouseEvent("contextmenu", {
          bubbles: true, cancelable: true, composed: true, view: window,
          clientX: at.x, clientY: at.y, button: 0, buttons: 1, ctrlKey: true
        }))""",
        {"x": x, "y": y},
    )
    page.mouse.up()
    page.keyboard.up("Control")


def test_a_right_click_on_a_thumbnail_opens_the_pages_menu(editor):
    """A10"""
    page = three(editor)
    watch(page)
    right_thumb(page, 1)
    assert kept(page)
    expect(page.get_by_role("menuitem")).to_have_text(
        [
            "Neue Seite",
            "Seite duplizieren",
            "Seite löschen",
            re.compile("^Ausschneiden"),
            re.compile("^Kopieren"),
            re.compile("^Einfügen"),
        ]
    )


def test_a_ctrl_click_sent_as_the_main_button_opens_the_pages_menu(editor):
    """#171. Chrome on a Mac may send Ctrl+click as the main button. The pages' menu still opens."""
    page = three(editor)
    watch(page)
    ctrl_click_as_main_button(page, 1)
    expect(menu(page)).to_be_visible()
    assert kept(page)
    expect(page.get_by_role("menuitem")).to_have_text(
        [
            "Neue Seite",
            "Seite duplizieren",
            "Seite löschen",
            re.compile("^Ausschneiden"),
            re.compile("^Kopieren"),
            re.compile("^Einfügen"),
        ]
    )
    # As a right click on a thumbnail that was not chosen: that page alone, and no drag.
    expect_in_use(page, 1)
    expect_order(page, "abc")


def test_a_ctrl_click_sent_as_the_main_button_chooses_as_a_right_click(editor):
    """#171. A chosen thumbnail keeps the choice; another is chosen alone. The pages stay put."""
    page = three(editor)
    pick_many(page, 0, 1)
    ctrl_click_as_main_button(page, 1)
    expect(menu(page)).to_be_visible()
    expect_chosen(page, 0, 1)
    page.keyboard.press("Escape")
    expect(menu(page)).to_have_count(0)
    ctrl_click_as_main_button(page, 2)
    expect(menu(page)).to_be_visible()
    expect_chosen(page, 2)
    expect_order(page, "abc")


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


def test_seite_loeschen_is_off_with_one_page(editor):
    """I4"""
    page = editor(*texts("a"), theme="")
    right_thumb(page, 0)
    expect(item(page, "Seite löschen")).to_be_disabled()
    expect(item(page, "Neue Seite")).to_be_enabled()
    expect(item(page, "Seite duplizieren")).to_be_enabled()


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
