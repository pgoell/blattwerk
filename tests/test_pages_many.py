"""Pages chosen in the panel Seiten with Ctrl+click or Shift+click move, copy and go together."""

from playwright.sync_api import expect
from test_pages import expect_order, half, three
from ui import centre, drag, thumb


def choose(page, n, *modifiers):
    thumb(page, n).click(modifiers=list(modifiers))


def pick_many(page, *ns):
    """Chooses thumbnails n of `ns` with Ctrl+click, the first one by a plain click."""
    choose(page, ns[0])
    for n in ns[1:]:
        choose(page, n, "ControlOrMeta")


def expect_chosen(page, *ns):
    for n in range(page.locator(".pages [data-thumb]").count()):
        expect(thumb(page, n)).to_have_attribute("aria-pressed", "true" if n in ns else "false")


def panel(page, label):
    return page.locator(".left .head").get_by_role("button", name=label, exact=True)


def menu_item(page, name):
    return page.get_by_role("menuitem", name=name, exact=True)


def test_ctrl_click_adds_and_drops_a_thumbnail_from_the_choice(editor):
    """Ctrl+click adds a page to the choice and a second Ctrl+click drops it."""
    page = three(editor)
    pick_many(page, 0, 2)
    expect_chosen(page, 0, 2)
    choose(page, 2, "ControlOrMeta")
    expect_chosen(page, 0)


def test_shift_click_chooses_the_range_from_the_page_in_use(editor):
    """Shift+click picks every page from the page in use to the clicked one."""
    page = three(editor)
    choose(page, 0)
    choose(page, 2, "Shift")
    expect_chosen(page, 0, 1, 2)


def test_a_drag_of_a_chosen_thumbnail_moves_all_chosen_pages_together(editor):
    """Pages a and b, dragged after c, land together in order; one undo takes it back."""
    page = three(editor)
    pick_many(page, 0, 1)
    drag(page, centre(thumb(page, 1)), half(page, 2, "right"))
    expect_order(page, "cab")
    expect(page.locator(".sheet.on")).to_have_attribute("data-page", "1")
    page.keyboard.press("Control+z")
    expect_order(page, "abc")
    page.keyboard.press("Control+y")
    expect_order(page, "cab")


def test_duplicate_copies_all_chosen_pages_after_the_last_of_them(editor):
    """Seite duplizieren on pages 1 and 3 copies both after page 3; one undo takes both away."""
    page = three(editor)
    pick_many(page, 0, 2)
    panel(page, "Seite duplizieren").click()
    expect_order(page, "abc++")
    page.keyboard.press("Control+z")
    expect_order(page, "abc")


def test_duplicate_key_copies_all_chosen_pages(editor):
    """Ctrl+D on a chosen thumbnail copies all chosen pages."""
    page = three(editor)
    pick_many(page, 0, 1)
    page.keyboard.press("Control+d")
    expect_order(page, "ab++c")


def test_delete_from_the_panel_head_takes_all_chosen_pages(editor):
    """Seite löschen in the panel head takes both chosen pages; one undo brings them back."""
    page = three(editor)
    pick_many(page, 0, 1)
    panel(page, "Seite löschen").click()
    expect_order(page, "c")
    page.keyboard.press("Control+z")
    expect_order(page, "abc")
    page.keyboard.press("Control+y")
    expect_order(page, "c")


def test_delete_from_the_thumbnail_menu_takes_all_chosen_pages(editor):
    """The thumbnail menu's Seite löschen takes all chosen pages; a right-click keeps the choice."""
    page = three(editor)
    pick_many(page, 0, 2)
    thumb(page, 2).click(button="right")
    expect(menu_item(page, "Seite löschen")).to_be_enabled()
    expect_chosen(page, 0, 2)
    menu_item(page, "Seite löschen").click()
    expect_order(page, "b")


def test_delete_key_takes_all_chosen_pages(editor):
    """Delete on a chosen thumbnail takes all chosen pages."""
    page = three(editor)
    pick_many(page, 0, 2)
    page.keyboard.press("Delete")
    expect_order(page, "b")


def test_delete_key_on_the_last_pages_leaves_the_focus_on_a_thumbnail(editor):
    """The focus goes to the thumbnail in the place of the pages gone, so Delete again works on."""
    page = three(editor)
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    pick_many(page, 1, 2)
    page.keyboard.press("Delete")
    expect_order(page, "a")
    expect(thumb(page, 0)).to_be_focused()
    assert not errors


def test_the_last_page_never_goes_when_every_page_is_chosen(editor):
    """With every page chosen, delete is refused: the panel button and menu item are disabled."""
    page = three(editor)
    choose(page, 0)
    choose(page, 2, "Shift")
    expect(panel(page, "Seite löschen")).to_be_disabled()
    thumb(page, 1).click(button="right")
    expect(menu_item(page, "Seite löschen")).to_be_disabled()
    page.keyboard.press("Escape")
    page.keyboard.press("Delete")
    expect_order(page, "abc")


def test_right_click_on_a_chosen_thumbnail_keeps_the_choice(editor):
    """A right-click on a chosen page keeps the choice; on an unchosen one it chooses only that."""
    page = three(editor)
    pick_many(page, 0, 1)
    thumb(page, 1).click(button="right")
    expect_chosen(page, 0, 1)
    page.keyboard.press("Escape")
    thumb(page, 2).click(button="right")
    expect_chosen(page, 2)
    page.keyboard.press("Escape")


def test_a_plain_click_after_a_choice_leaves_just_that_page(editor):
    """A plain click after a choice leaves only the clicked page chosen."""
    page = three(editor)
    pick_many(page, 0, 1)
    choose(page, 2)
    expect_chosen(page, 2)


def test_ctrl_arrow_moves_all_chosen_pages_by_one_place(editor):
    """Ctrl+ArrowDown on a chosen thumbnail moves both chosen pages one place, in order."""
    page = three(editor)
    pick_many(page, 0, 1)
    thumb(page, 1).focus()
    page.keyboard.press("Control+ArrowDown")
    expect_order(page, "cab")
    page.keyboard.press("Control+z")
    expect_order(page, "abc")


def test_ctrl_shift_arrow_moves_all_chosen_pages_to_the_end(editor):
    """Ctrl+Shift+ArrowDown moves both chosen pages to the end, in order."""
    page = three(editor)
    pick_many(page, 0, 1)
    thumb(page, 1).focus()
    page.keyboard.press("Control+Shift+ArrowDown")
    expect_order(page, "cab")
