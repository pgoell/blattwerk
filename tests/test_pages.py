"""Pages move by a drag of their thumbnail or by the keys, and "Seite duplizieren" copies one."""

import re

import pytest
from playwright.sync_api import expect
from test_clipboard import every
from ui import FIELD, TEXT, at, box, centre, doc, drag, hold_drag, order, pick, swipe, thumb, user

DRAG = re.compile(r"\bdrag\b")
ON = re.compile(r"\bon\b")
# What a page can have of its own.
OWN = {"guides": {"x": [70], "y": [120, 200]}, "grid": 5, "landscape": True}


def three(editor, **more):
    """Three pages with one text each, "a", "b" and "c", and the panel Seiten open."""
    rest = [{"blocks": [box(name, "text", TEXT)]} for name in "bc"]
    return editor(box("a", "text", TEXT), pages=rest, theme="", **more)


def expect_order(page, names):
    """Waits until the pages hold these blocks, one each. "+" is a copy: a block with a new name."""
    expect(page.locator(".sheet[data-page]")).to_have_count(len(names))
    for n, name in enumerate(names):
        held = page.locator(f'.sheet[data-page="{n}"] .block[data-id]')
        expect(held).to_have_count(1)
        if name != "+":
            expect(held).to_have_attribute("data-id", name)
    assert [b if b in names else "+" for [b] in order(page)] == list(names)


def expect_in_use(page, n):
    expect(page.locator(f'.sheet[data-page="{n}"]')).to_have_class(ON)
    expect(page.locator(".sheet.on")).to_have_count(1)
    expect(thumb(page, n)).to_have_attribute("aria-pressed", "true")
    expect(page.locator('.pages [aria-pressed="true"]')).to_have_count(1)


def half(page, n, side):
    """A point on the left or the right half of thumbnail n: a drop there is before or after it."""
    held = thumb(page, n).bounding_box()
    across = 0.25 if side == "left" else 0.75
    return held["x"] + held["width"] * across, held["y"] + held["height"] / 2


def pull(page, n, to, side):
    """Drags thumbnail n with the mouse onto a half of thumbnail `to`."""
    drag(page, centre(thumb(page, n)), half(page, to, side))


def lift(page, n, to, side):
    """As `pull`, with the mouse still down at the end."""
    page.mouse.move(*centre(thumb(page, n)))
    page.mouse.down()
    page.mouse.move(*half(page, to, side), steps=5)


def copy(page):
    return page.get_by_role("button", name="Seite duplizieren", exact=True)


def expect_no_drag(page):
    expect(page.locator(".pages .mark")).to_have_count(0)
    expect(page.locator(".pages .drag")).to_have_count(0)


def names(pages):
    return [[b["id"] for b in p["blocks"]] for p in pages]


def left(page, name):
    return at(page, name).evaluate("el => getComputedStyle(el).left")


def write(page, name, words):
    """Opens the text and types over all of it. The text stays open."""
    pick(page, name)
    page.keyboard.press("Enter")
    page.keyboard.type(words)
    expect(page.locator(FIELD)).to_have_text(words)


@pytest.mark.parametrize(
    ("n", "to", "side", "after"),
    [(0, 2, "right", "bca"), (2, 0, "left", "cab"), (0, 1, "right", "bac"), (2, 1, "left", "acb")],
)
def test_a_thumbnail_dragged_with_the_mouse_moves_its_page_to_the_drop(editor, n, to, side, after):
    """A1"""
    page = three(editor)
    pull(page, n, to, side)
    expect_order(page, after)
    expect_no_drag(page)


def test_a_thumbnail_dropped_below_the_last_one_moves_its_page_to_the_end(editor):
    """A1"""
    page = three(editor)
    last = thumb(page, 2).bounding_box()
    drag(
        page,
        centre(thumb(page, 0)),
        (last["x"] + last["width"] / 2, last["y"] + last["height"] + 8),
    )
    expect_order(page, "bca")


def test_a_moved_page_keeps_its_blocks_guide_lines_grid_and_format(editor):
    """A1"""
    client = user()
    rest = [{"blocks": [box("b", "text", TEXT)], **OWN}, {"blocks": [box("c", "text", TEXT)]}]
    page = editor(box("a", "text", TEXT), client=client, pages=rest, theme="")
    pull(page, 1, 0, "left")
    expect_order(page, "bac")
    first, second, third = doc(page, client)["pages"]
    assert {key: first[key] for key in OWN} == OWN
    assert first["blocks"][0]["props"] == TEXT
    assert names([first, second, third]) == [["b"], ["a"], ["c"]]
    assert not OWN.keys() & (second.keys() | third.keys())


def test_a_held_thumbnail_follows_the_finger(editor):
    """A2"""
    page = three(editor, touch=True)
    start, end = centre(thumb(page, 0)), half(page, 2, "right")
    hold_drag(page, thumb(page, 0), start, half(page, 1, "left"), end)
    expect_order(page, "bca")
    expect_no_drag(page)


def test_a_short_swipe_over_the_thumbnails_moves_no_page(editor):
    """A2"""
    page = three(editor, touch=True)
    swipe(page, centre(thumb(page, 0)), half(page, 1, "left"), half(page, 2, "right"))
    expect_no_drag(page)
    expect_order(page, "abc")


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


def test_a_move_is_saved(editor):
    """A7"""
    client = user()
    page = three(editor, client=client)
    pull(page, 0, 2, "right")
    expect_order(page, "bca")
    assert names(doc(page, client)["pages"]) == [["b"], ["c"], ["a"]]


def test_a_copy_is_saved(editor):
    """A7"""
    client = user()
    page = three(editor, client=client)
    copy(page).click()
    expect_order(page, "a+bc")
    assert names(doc(page, client)["pages"]) == order(page)


def test_undo_and_redo_take_a_move_as_one_step(editor):
    """I1"""
    page = three(editor)
    pull(page, 0, 2, "right")
    expect_order(page, "bca")
    page.keyboard.press("Control+z")
    expect_order(page, "abc")
    page.keyboard.press("Control+y")
    expect_order(page, "bca")
    page.keyboard.press("Control+z")
    expect_order(page, "abc")


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


def test_the_moved_page_is_the_page_in_use_after_the_drop(editor):
    """I2"""
    page = three(editor)
    thumb(page, 1).click()
    expect_in_use(page, 1)
    pull(page, 2, 0, "left")
    expect_order(page, "cab")
    expect_in_use(page, 0)


def test_the_copy_is_the_page_in_use_with_nothing_selected(editor):
    """I2"""
    page = three(editor)
    pick(page, "a")
    copy(page).click()
    expect_order(page, "a+bc")
    expect_in_use(page, 1)
    expect(page.locator(".block.sel")).to_have_count(0)


def test_a_click_on_a_thumbnail_only_visits_its_page(editor):
    """I3"""
    page = three(editor)
    thumb(page, 2).click()
    expect_in_use(page, 2)
    expect_no_drag(page)
    expect_order(page, "abc")


def test_enter_on_a_thumbnail_visits_its_page_after_a_drag(editor):
    """I3: the drag swallows its own click only."""
    page = three(editor)
    pull(page, 2, 0, "left")
    expect_order(page, "cab")
    thumb(page, 2).focus()
    page.keyboard.press("Enter")
    expect_in_use(page, 2)


@pytest.mark.parametrize(("to", "side"), [(1, "left"), (1, "right"), (0, "right")])
def test_a_drop_at_the_pages_own_place_leaves_nothing_to_undo(editor, to, side):
    """I3"""
    page = three(editor)
    # Another change first: it is what undo takes back if the drop after it changes nothing.
    pick(page, "a")
    before = left(page, "a")
    page.keyboard.press("ArrowRight")
    expect(at(page, "a")).not_to_have_css("left", before)
    pull(page, 1, to, side)
    expect_no_drag(page)
    expect_order(page, "abc")
    page.keyboard.press("Control+z")
    expect(at(page, "a")).to_have_css("left", before)
    expect_order(page, "abc")


def test_a_line_marks_where_the_page_will_land_and_the_thumbnail_fades(editor):
    """I4"""
    page = three(editor)
    expect_no_drag(page)
    lift(page, 0, 2, "right")
    expect(thumb(page, 0)).to_have_class(DRAG)
    expect(thumb(page, 0)).not_to_have_css("opacity", "1")
    expect(page.locator(".pages .mark")).to_have_count(1)
    expect(page.locator(".pages .mark")).to_have_attribute("data-to", "2")
    page.mouse.move(*half(page, 1, "right"), steps=5)
    expect(page.locator(".pages .mark")).to_have_attribute("data-to", "1")
    page.mouse.move(*half(page, 1, "left"), steps=5)
    expect(page.locator(".pages .mark")).to_have_attribute("data-to", "0")
    page.mouse.move(*half(page, 1, "right"), steps=5)
    page.mouse.up()
    expect_no_drag(page)
    expect_order(page, "bac")


def test_escape_calls_a_drag_off(editor):
    """I5"""
    page = three(editor)
    lift(page, 0, 2, "right")
    expect(page.locator(".pages .mark")).to_have_count(1)
    page.keyboard.press("Escape")
    expect_no_drag(page)
    page.mouse.up()
    expect_no_drag(page)
    expect_order(page, "abc")


def test_a_text_open_for_typing_keeps_its_words_when_its_page_moves(editor):
    """I6"""
    page = three(editor)
    write(page, "a", "du")
    pull(page, 0, 2, "right")
    expect_order(page, "bca")
    expect(at(page, "a")).to_contain_text("du")


def test_a_text_open_for_typing_gives_its_words_to_the_copy(editor):
    """I6"""
    page = three(editor)
    write(page, "a", "du")
    copy(page).click()
    expect_order(page, "a+bc")
    expect(at(page, "a")).to_contain_text("du")
    expect(page.locator('.sheet[data-page="1"] .block[data-id]')).to_contain_text("du")


def test_ctrl_and_an_arrow_on_a_thumbnail_move_its_page_by_one_place(editor):
    """I7"""
    page = three(editor)
    thumb(page, 0).focus()
    page.keyboard.press("Control+ArrowDown")
    expect_order(page, "bac")
    expect(thumb(page, 1)).to_be_focused()
    # The focus went with the page, so the same key moves it on.
    page.keyboard.press("Control+ArrowDown")
    expect_order(page, "bca")
    expect(thumb(page, 2)).to_be_focused()
    page.keyboard.press("Control+ArrowUp")
    expect_order(page, "bac")
    expect(thumb(page, 1)).to_be_focused()


def test_ctrl_shift_and_an_arrow_on_a_thumbnail_move_its_page_to_the_start_or_the_end(editor):
    """I7"""
    page = three(editor)
    thumb(page, 0).focus()
    page.keyboard.press("Control+Shift+ArrowDown")
    expect_order(page, "bca")
    expect(thumb(page, 2)).to_be_focused()
    page.keyboard.press("Control+Shift+ArrowUp")
    expect_order(page, "abc")
    expect(thumb(page, 0)).to_be_focused()


def test_ctrl_d_on_a_thumbnail_copies_its_page(editor):
    """I7"""
    page = three(editor)
    thumb(page, 1).focus()
    page.keyboard.press("Control+d")
    expect_order(page, "ab+c")
    expect(thumb(page, 2)).to_be_focused()


def test_in_a_text_the_page_keys_stay_the_texts(editor):
    """I7"""
    page = three(editor)
    write(page, "a", "du")
    for keys in ("ArrowDown", "ArrowUp", "Shift+ArrowDown", "Shift+ArrowUp", "d"):
        page.keyboard.press(f"Control+{keys}")
        expect(page.locator(FIELD)).to_have_text("du")
        expect_order(page, "abc")
