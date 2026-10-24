"""Seite duplizieren: the copy, what it keeps, and that it is one undo step.

The helpers live in test_pages.py.
"""

from playwright.sync_api import expect
from test_clipboard import every
from test_pages import (
    OWN,
    copy,
    expect_in_use,
    expect_order,
    left,
    names,
    three,
    write,
)
from ui import (
    TEXT,
    at,
    box,
    doc,
    order,
    pick,
    thumb,
    user,
)


def test_seite_duplizieren_puts_a_copy_right_after_the_page_in_use(editor):
    """A3"""
    page = three(editor)
    thumb(page, 1).click()
    expect_in_use(page, 1)
    copy(page).click()
    expect_order(page, "ab+c")
    expect(page.locator(".pages button[data-thumb]")).to_have_count(4)


def test_the_left_bar_of_the_leaf_theme_copies_the_page_too(editor):
    """A3"""
    rest = [{"blocks": [box("b", "text", TEXT)]}]
    page = editor(box("a", "text", TEXT), pages=rest, theme="leaf")
    page.locator("aside.left .insert").get_by_role("button", name="Seite duplizieren").click()
    expect_order(page, "a+b")


def test_the_copy_holds_every_block_of_every_type_under_new_names(editor):
    """A4"""
    client = user()
    blocks = every(client)
    page = editor(*blocks, client=client, theme="")
    copy(page).click()
    expect(page.locator('.sheet[data-page="1"] .block[data-id]')).to_have_count(len(blocks))
    old, new = (sorted(p["blocks"], key=lambda b: b["z"]) for p in doc(page, client)["pages"])
    bare = [[{k: b[k] for k in b if k not in ("id", "group")} for b in held] for held in (old, new)]
    assert bare[1] == bare[0]
    ids = [b["id"] for b in old + new]
    assert len(set(ids)) == len(ids)
    # A group stays one group, of the copy's own.
    assert ["group" in b for b in new] == ["group" in b for b in old]
    [was], [group] = ({tuple(b["group"]) for b in held if "group" in b} for held in (old, new))
    assert len(group) == 1
    assert group != was


def test_a_change_to_the_copy_leaves_the_original_alone(editor):
    """A4"""
    page = editor(box("a", "text", TEXT), theme="")
    copy(page).click()
    expect_order(page, "a+")
    before = left(page, "a")
    twin = page.locator('.sheet[data-page="1"] .block[data-id]')
    expect(twin).to_have_css("left", before)
    twin.click()
    expect(page.locator('.sheet[data-page="1"] .block.sel')).to_have_count(1)
    page.keyboard.press("ArrowRight")
    expect(twin).not_to_have_css("left", before)
    expect(at(page, "a")).to_have_css("left", before)


def test_the_copy_holds_the_pages_own_guide_lines_grid_and_format(editor):
    """A5"""
    client = user()
    rest = [{"blocks": [box("b", "text", TEXT)], **OWN}]
    page = editor(box("a", "text", TEXT), client=client, pages=rest, theme="")
    thumb(page, 1).click()
    expect_in_use(page, 1)
    copy(page).click()
    expect_order(page, "ab+")
    first, second, third = doc(page, client)["pages"]
    assert {key: third[key] for key in OWN} == OWN
    assert {key: second[key] for key in OWN} == OWN
    assert not OWN.keys() & first.keys()


def test_a_tap_on_seite_duplizieren_copies_the_page(editor):
    """A6"""
    page = three(editor, touch=True)
    copy(page).tap()
    expect_order(page, "a+bc")


def test_a_copy_is_saved(editor):
    """A7"""
    client = user()
    page = three(editor, client=client)
    copy(page).click()
    expect_order(page, "a+bc")
    assert names(doc(page, client)["pages"]) == order(page)


def test_undo_and_redo_take_a_copy_as_one_step(editor):
    """I1"""
    page = three(editor)
    copy(page).click()
    expect_order(page, "a+bc")
    page.keyboard.press("Control+z")
    expect_order(page, "abc")
    page.keyboard.press("Control+y")
    expect_order(page, "a+bc")
    page.keyboard.press("Control+z")
    expect_order(page, "abc")


def test_the_copy_is_the_page_in_use_with_nothing_selected(editor):
    """I2"""
    page = three(editor)
    pick(page, "a")
    copy(page).click()
    expect_order(page, "a+bc")
    expect_in_use(page, 1)
    expect(page.locator(".block.sel")).to_have_count(0)


def test_a_text_open_for_typing_gives_its_words_to_the_copy(editor):
    """I6"""
    page = three(editor)
    write(page, "a", "du")
    copy(page).click()
    expect_order(page, "a+bc")
    expect(at(page, "a")).to_contain_text("du")
    expect(page.locator('.sheet[data-page="1"] .block[data-id]')).to_contain_text("du")


def test_ctrl_d_on_a_thumbnail_copies_its_page(editor):
    """I7"""
    page = three(editor)
    # With a block selected too: the key is the thumbnail's, and no block is copied.
    pick(page, "a")
    thumb(page, 1).focus()
    page.keyboard.press("Control+d")
    expect_order(page, "ab+c")
    expect(thumb(page, 2)).to_be_focused()
