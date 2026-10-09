"""Pages move by a drag of their thumbnail or by the keys, and "Seite duplizieren" copies one."""

import re

import pytest
from playwright.sync_api import expect
from test_clipboard import button, every
from test_drop import PNG, spot
from ui import (
    BROWSER,
    FIELD,
    RECT,
    TEXT,
    at,
    box,
    centre,
    copy_picture,
    doc,
    drag,
    drop,
    finger,
    hold_drag,
    jitter,
    order,
    outlast,
    pick,
    swipe,
    thumb,
    user,
)

DRAG = re.compile(r"\bdrag\b")
ON = re.compile(r"\bon\b")
# How far a held finger strays from where it came down, in px: a few each way, and almost 10.
JITTER = [((3, 0), (0, 4), (-2, 2)), ((0, 9),), ((-6, -7),)]
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


@pytest.mark.parametrize("by", JITTER)
def test_a_held_thumbnail_follows_a_finger_that_jitters(editor, by):
    """B1"""
    page = three(editor, touch=True)
    start, end = centre(thumb(page, 0)), half(page, 2, "right")
    hold_drag(page, thumb(page, 0), start, half(page, 1, "left"), end, by=by)
    expect_order(page, "bca")
    expect_no_drag(page)


def test_a_finger_that_moves_14_px_and_then_rests_on_a_thumbnail_drags_no_page(editor):
    """B2"""
    page = three(editor, touch=True)
    start = centre(thumb(page, 0))
    with finger(page, start) as touch:
        jitter(thumb(page, 0), start, (14, 0))
        outlast(page)
        expect_no_drag(page)
        touch("touchMove", half(page, 1, "left"))
        touch("touchMove", half(page, 2, "right"))
        expect_no_drag(page)
    expect_order(page, "abc")


@pytest.mark.parametrize("by", [(), (3, 0), (0, 9)])
def test_a_finger_lifted_before_the_hold_is_over_only_visits_the_page(editor, by):
    """I4"""
    page = three(editor, touch=True)
    start = centre(thumb(page, 2))
    with finger(page, start):
        jitter(thumb(page, 2), start, *([by] if by else []))
    expect_in_use(page, 2)
    expect_no_drag(page)
    expect_order(page, "abc")


def test_a_second_finger_calls_the_hold_on_a_thumbnail_off(editor):
    """I5"""
    page = three(editor, touch=True)
    start, other = centre(thumb(page, 0)), centre(thumb(page, 1))
    with finger(page, start) as touch:
        touch("touchStart", start, other)
        outlast(page)
        expect_no_drag(page)
    expect_order(page, "abc")


def test_a_second_finger_beside_the_panel_calls_the_hold_on_a_thumbnail_off(editor):
    """I5"""
    page = three(editor, touch=True)
    (x, y), other = centre(thumb(page, 0)), centre(page.locator('.sheet[data-page="0"]'))
    with finger(page, (x, y)) as touch:
        # The panel hears of a finger on the sheet with the first finger's next move.
        if BROWSER == "webkit":
            # WebKit keeps no move back, so the fingers themselves come down and move.
            touch("touchStart", (x, y), other)
            touch("touchMove", (x + 3, y), other)
        else:
            thumb(page, 0).evaluate(
                """(el, [x, y, ox, oy]) => {
                    const at = (identifier, clientX, clientY) =>
                        new Touch({ identifier, target: el, clientX, clientY });
                    const touches = [at(0, x + 3, y), at(1, ox, oy)];
                    el.dispatchEvent(new TouchEvent("touchmove", { touches, bubbles: true }));
                }""",
                [x, y, *other],
            )
        outlast(page)
        expect_no_drag(page)
    expect_order(page, "abc")


def test_undo_and_redo_take_a_move_after_a_jittered_hold_as_one_step(editor):
    """I6"""
    page = three(editor, touch=True)
    start, end = centre(thumb(page, 0)), half(page, 2, "right")
    hold_drag(page, thumb(page, 0), start, half(page, 1, "left"), end, by=JITTER[0])
    expect_order(page, "bca")
    page.keyboard.press("Control+z")
    expect_order(page, "abc")
    page.keyboard.press("Control+y")
    expect_order(page, "bca")
    page.keyboard.press("Control+z")
    expect_order(page, "abc")


def test_a_short_swipe_over_the_thumbnails_moves_no_page(editor):
    """A2"""
    page = three(editor, touch=True)
    swipe(page, centre(thumb(page, 0)), half(page, 1, "left"), half(page, 2, "right"))
    expect_no_drag(page)
    expect_order(page, "abc")


@pytest.mark.webkit_xfail(205, "no browser scrolls for the touch events a page dispatches")
def test_a_swipe_over_many_thumbnails_scrolls_the_panel_and_moves_no_page(editor):
    """A2"""
    names = "abcdefghijklmn"
    rest = [{"blocks": [box(name, "text", TEXT)]} for name in names[1:]]
    page = editor(box("a", "text", TEXT), pages=rest, theme="", touch=True)
    panel = page.locator("aside.left")
    assert panel.evaluate("el => el.scrollHeight > el.clientHeight")
    x, y = centre(thumb(page, 6))
    swipe(page, *((x, y - 30 * i) for i in range(12)))
    page.wait_for_function("document.querySelector('aside.left').scrollTop > 0", timeout=2000)
    expect_no_drag(page)
    expect_order(page, names)


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


def expect_mark(page, n, side):
    """Waits until the line is drawn left or right of thumbnail n, in its row."""
    page.wait_for_function(
        """([n, right]) => {
            const mark = document.querySelector(".pages .mark")?.getBoundingClientRect();
            const by = document.querySelector(`.pages [data-thumb="${n}"]`).getBoundingClientRect();
            if (!mark) return false;
            // The dragged thumbnail is drawn smaller, so the line may be longer than it.
            const middle = (mark.top + mark.bottom) / 2;
            const row = middle > by.top && middle < by.bottom && mark.height < 1.2 * by.height;
            return row && (right ? mark.left >= by.right : mark.right <= by.left);
        }""",
        arg=[n, side == "right"],
        timeout=2000,
    )


def test_the_line_is_drawn_in_the_row_of_the_thumbnail_under_the_pointer(editor):
    """I4. Thumbnails 0 and 1 share a row: after 1 is the end of that row, not the next one's."""
    page = three(editor)
    lift(page, 0, 1, "right")
    expect(page.locator(".pages .mark")).to_have_attribute("data-to", "1")
    expect_mark(page, 1, "right")
    page.mouse.move(*half(page, 2, "left"), steps=5)
    expect_mark(page, 2, "left")
    expect(page.locator(".pages .mark")).to_have_attribute("data-to", "1")
    page.mouse.move(*half(page, 1, "left"), steps=5)
    expect_mark(page, 1, "left")
    expect_mark(page, 0, "right")
    expect(page.locator(".pages .mark")).to_have_attribute("data-to", "0")
    page.mouse.up()
    expect_no_drag(page)
    expect_order(page, "abc")


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
    # With a block selected too: the key is the thumbnail's, and no block is copied.
    pick(page, "a")
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


def test_a_dropped_picture_finds_its_page_after_a_change_and_a_move(editor):
    """The upload ends after the page dropped on has changed and another has moved before it."""
    page = three(editor)
    waiting = []
    page.route("**/api/uploads", lambda route: waiting.append(route))
    with page.expect_request("**/api/uploads"):
        drop(page, *spot(page, 105, 148.5), PNG)
    pick(page, "a")
    before = left(page, "a")
    page.keyboard.press("ArrowRight")
    expect(at(page, "a")).not_to_have_css("left", before)
    pull(page, 2, 0, "left")
    expect_order(page, "cab")
    [route] = waiting
    route.continue_()
    held = [page.locator(f'.sheet[data-page="{n}"] .block[data-id]') for n in range(3)]
    expect(held[1]).to_have_count(2)
    expect(held[1].locator(".picture img")).to_have_js_property("naturalWidth", 3)
    expect(held[0]).to_have_count(1)
    expect(held[2]).to_have_count(1)
    assert "a" in order(page)[1]


# What changes the pages with "b", the second of three, in use: how many pages there are then,
# which is in use, where a block asked for on "b" lands and how many blocks the sheet then has.
# With "b" deleted the block lands on the page in use.
CHANGES = {
    "new": (lambda page: button(page, "Neue Seite").click(), 4, 2, 1, 4),
    "deleted": (lambda page: button(page, "Seite löschen").click(), 2, 1, 1, 3),
    "moved": (lambda page: page.keyboard.press("Control+ArrowUp"), 3, 0, 0, 4),
    "copied": (lambda page: copy(page).click(), 4, 2, 1, 5),
}


def change_pages(page, how):
    """Changes the pages and waits for it. Gives the page in use from then on."""
    run, count, after, _, _ = CHANGES[how]
    thumb(page, 1).focus()
    run(page)
    expect(page.locator(".sheet[data-page]")).to_have_count(count)
    expect_in_use(page, after)
    return after


def expect_shown(page, n):
    """Waits until page n is in use and the desk has scrolled to it."""
    expect_in_use(page, n)
    expect(page.locator(f'.sheet[data-page="{n}"]')).to_be_in_viewport(ratio=0.5)


@pytest.mark.parametrize("how", CHANGES)
def test_undo_and_redo_of_a_page_change_show_the_page_it_changed(editor, how):
    """#155: undo shows the page in use before the change, redo the one in use after it."""
    page = three(editor)
    thumb(page, 1).click()
    expect_in_use(page, 1)
    after = change_pages(page, how)
    away = 0 if after else 2
    thumb(page, away).click()
    expect_shown(page, away)
    page.keyboard.press("Control+z")
    expect_order(page, "abc")
    expect_shown(page, 1)
    thumb(page, 2 - away).click()
    expect_shown(page, 2 - away)
    page.keyboard.press("Control+y")
    expect(page.locator(".sheet[data-page]")).to_have_count(CHANGES[how][1])
    expect_shown(page, after)


def test_undo_and_redo_of_a_block_change_show_its_page(editor):
    """#155"""
    page = three(editor)
    pick(page, "b")
    before = left(page, "b")
    page.keyboard.press("ArrowRight")
    expect(at(page, "b")).not_to_have_css("left", before)
    thumb(page, 0).click()
    expect_shown(page, 0)
    page.keyboard.press("Control+z")
    expect(at(page, "b")).to_have_css("left", before)
    expect_shown(page, 1)
    thumb(page, 2).click()
    expect_shown(page, 2)
    page.keyboard.press("Control+y")
    expect(at(page, "b")).not_to_have_css("left", before)
    expect_shown(page, 1)


def test_undo_of_a_change_on_the_page_in_use_keeps_the_selection(editor):
    """#155: the selection stays when the undo is for the page in use."""
    page = three(editor)
    pick(page, "b")
    before = left(page, "b")
    page.keyboard.press("ArrowRight")
    expect(at(page, "b")).not_to_have_css("left", before)
    page.keyboard.press("Control+z")
    expect(at(page, "b")).to_have_css("left", before)
    expect_in_use(page, 1)
    expect(at(page, "b")).to_have_class("block sel")


PICKED = {"name": "bild.png", "mimeType": "image/png", "buffer": PNG[2]}
PICKER = "input[type=file]"
# What asks the server for a block, and the request that waits.
SOURCES = {
    "maths": ("**/api/maths", lambda page: button(page, "Rechnen").click()),
    "ctrl v": ("**/api/uploads", lambda page: page.keyboard.press("Control+v")),
    "einfügen": ("**/api/uploads", lambda page: button(page, "Einfügen").click()),
    "picker": ("**/api/uploads", lambda page: page.locator(PICKER).set_input_files(PICKED)),
}
# The sources that paste a picture another app copied, which WebKit's clipboard does not hold.
PASTES = ("ctrl v", "einfügen")
NO_PICTURE = pytest.mark.webkit_xfail(
    204, "headless WebKit on Linux keeps no picture on the clipboard"
)


@pytest.mark.parametrize("how", CHANGES)
@pytest.mark.parametrize(
    "source", [pytest.param(s, marks=NO_PICTURE if s in PASTES else ()) for s in SOURCES]
)
def test_a_block_on_its_way_finds_its_page_after_the_pages_change(editor, source, how):
    """#156: it lands on the page in use when it was asked for, wherever that page is by then."""
    page = three(editor)
    url, ask = SOURCES[source]
    if url.endswith("uploads"):
        copy_picture(page)
    thumb(page, 1).click()
    expect_in_use(page, 1)
    # The server's answer waits until the pages have changed.
    waiting = []
    page.route(url, lambda route: waiting.append(route))
    with page.expect_request(url):
        ask(page)
    change_pages(page, how)
    _, _, _, n, count = CHANGES[how]
    [route] = waiting
    route.continue_()
    expect(page.locator(".block[data-id]")).to_have_count(count)
    expect(page.locator(f'.sheet[data-page="{n}"] .block[data-id]')).to_have_count(2)
    expect(page.locator(f'.sheet[data-page="{n}"] .block.sel')).to_have_count(1)
    expect(page.locator(".block.sel")).to_have_count(1)
    expect_in_use(page, n)
    assert "b" in order(page)[n] or how == "deleted"


def test_undo_of_a_brush_stroke_on_another_page_shows_that_page(editor):
    """The press that paints also visits the page: the paint comes off where it went on."""
    red = box("a", "shape", {**RECT, "fill": "#ff0000"})
    page = editor(red, more=[box("b", "shape", RECT)], theme="")
    pick(page, "a")
    page.get_by_label("Format übertragen", exact=True).click()
    was = at(page, "b").inner_html()
    same = "([was, same]) => (document.querySelector('[data-id=b]').innerHTML === was) === same"
    at(page, "b").click()
    expect_in_use(page, 1)
    page.wait_for_function(same, arg=[was, False])
    page.keyboard.press("Control+z")
    page.wait_for_function(same, arg=[was, True])
    expect_shown(page, 1)


def test_undo_of_a_block_from_the_server_shows_the_page_it_landed_on(editor):
    page = three(editor)
    waiting = []
    page.route("**/api/maths", lambda route: waiting.append(route))
    with page.expect_request("**/api/maths"):
        button(page, "Rechnen").click()
    thumb(page, 2).click()
    expect_shown(page, 2)
    [route] = waiting
    route.continue_()
    expect(page.locator('.sheet[data-page="0"] .block[data-id]')).to_have_count(2)
    page.keyboard.press("Control+z")
    expect_order(page, "abc")
    expect_shown(page, 0)


def nudged(page):
    """Three pages with "a" moved by a key. Gives the page and where "a" was before."""
    page = three(page)
    pick(page, "a")
    before = left(page, "a")
    page.keyboard.press("ArrowRight")
    expect(at(page, "a")).not_to_have_css("left", before)
    return page, before


def test_undo_scrolls_to_the_page_in_use_when_it_is_out_of_view(editor):
    page, before = nudged(editor)
    page.locator(".desk").evaluate("el => el.scrollTo(0, el.scrollHeight)")
    expect(page.locator('.sheet[data-page="0"]')).not_to_be_in_viewport()
    page.keyboard.press("Control+z")
    expect(at(page, "a")).to_have_css("left", before)
    expect_shown(page, 0)


def test_undo_leaves_the_desk_where_it_is_while_its_page_is_in_view(editor):
    page, before = nudged(editor)
    page.locator(".desk").evaluate("el => el.scrollTo(0, 50)")
    page.keyboard.press("Control+z")
    expect(at(page, "a")).to_have_css("left", before)
    # A scroll would have begun by the second frame after the undo.
    page.evaluate("() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)))")
    assert page.locator(".desk").evaluate("el => el.scrollTop") == 50
