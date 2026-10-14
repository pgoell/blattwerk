"""The keys of the order: Ctrl+] and Ctrl+[ step it, with Shift to the front and the back."""

import pytest
from playwright.sync_api import expect
from test_menu import right, run
from test_order import KINDS, boxes, expect_stack, member, step
from ui import FIELD, RECT, at, box, expect_picked, pick, unpick, user


def key(page, name):
    page.keyboard.press(name)


@pytest.mark.parametrize("kind", KINDS)
def test_a_bracket_steps_every_kind(editor, kind):
    client = user()
    if kind == "group":
        page = editor(*boxes(*"abcd", grouped="ab"))
        at(page, "a").click()
        expect_picked(page, "a", "b")
        key(page, "Control+BracketRight")
        expect_stack(page, "cabd")
        key(page, "Control+BracketLeft")
        expect_stack(page, "abcd")
        return
    # The block "a" alone, with three blocks above it to step past.
    a = {k: v for k, v in member(kind, client).items() if k != "group"}
    page = editor(
        a,
        box("b", "shape", RECT, z=2, x=110, y=20, w=80),
        box("c", "shape", RECT, z=3, x=15, y=110, w=80),
        box("d", "shape", RECT, z=4, x=110, y=110, w=80),
        client=client,
    )
    # A flat line has no box to click: Tab with nothing picked picks the block at the back.
    unpick(page)
    key(page, "Tab")
    expect_picked(page, "a")
    key(page, "Control+BracketRight")
    expect_stack(page, "bacd")
    key(page, "Control+BracketLeft")
    expect_stack(page, "abcd")


def test_shift_goes_to_the_front_and_the_back(editor):
    page = editor(*boxes(*"abcd"))
    pick(page, "b")
    key(page, "Control+Shift+BracketRight")
    expect_stack(page, "acdb")
    key(page, "Control+Shift+BracketLeft")
    expect_stack(page, "bacd")


def test_a_group_and_several_blocks_step_by_key(editor):
    page = editor(*boxes(*"abcde", grouped="bc"))
    at(page, "b").click()
    expect_picked(page, "b", "c")
    key(page, "Control+BracketRight")
    expect_stack(page, "adbce")
    key(page, "Control+BracketLeft")
    expect_stack(page, "abcde")
    key(page, "Control+BracketLeft")
    expect_stack(page, "bcade")


def test_each_press_is_one_undo_step(editor):
    page = editor(*boxes(*"abcd"))
    pick(page, "a")
    key(page, "Control+BracketRight")
    key(page, "Control+BracketRight")
    expect_stack(page, "bcad")
    page.keyboard.press("Control+z")
    expect_stack(page, "bacd")
    page.keyboard.press("Control+z")
    expect_stack(page, "abcd")
    page.keyboard.press("Control+y")
    expect_stack(page, "bacd")


def test_keys_buttons_and_menu_agree(editor):
    page = editor(*boxes(*"abcd"))
    pick(page, "a")
    key(page, "Control+BracketRight")
    expect_stack(page, "bacd")
    step(page, "Eine nach vorn")
    expect_stack(page, "bcad")
    right(page, "a")
    run(page, "Eine Ebene nach vorn")
    expect_stack(page, "bcda")


def test_the_keys_do_nothing_while_writing(editor):
    page = editor(*boxes(*"abc"))
    pick(page, "a")
    page.keyboard.press("Enter")
    key(page, "Control+BracketRight")
    # A letter after it shows the key has been through, and the text is still open.
    page.keyboard.type("x")
    expect(page.locator(FIELD)).to_have_text("x")
    expect_stack(page, "abc")


def test_altgr_bracket_types_and_steps_nothing(editor):
    page = editor(*boxes(*"abc"))
    pick(page, "b")
    # Windows sends AltGr as Ctrl and Alt together; Playwright has no way to press it.
    page.evaluate(
        """() => {
            const event = { key: "]", ctrlKey: true, altKey: true, modifierAltGraph: true };
            (document.activeElement || document.body).dispatchEvent(
                new KeyboardEvent("keydown", { ...event, bubbles: true, cancelable: true }));
        }"""
    )
    expect_stack(page, "abc")


def test_a_part_of_a_group_steps_by_key(editor):
    page = editor(*boxes(*"abcde", grouped="bcd"))
    # One click picks the whole group, a second one the block alone.
    at(page, "b").click()
    expect_picked(page, "b", "c", "d")
    at(page, "b").click(force=True)
    expect_picked(page, "b")
    key(page, "Control+BracketRight")
    expect_stack(page, "acbde")
    key(page, "Control+BracketRight")
    expect_stack(page, "acdbe")
    # In front of its group it stays: one step back from there shows it never passed "e".
    key(page, "Control+BracketRight")
    key(page, "Control+BracketLeft")
    expect_stack(page, "acbde")


def test_a_key_at_the_end_leaves_nothing_to_undo(editor):
    page = editor(*boxes(*"abcd"))
    # Another change first: it is what undo takes back if the steps after it change nothing.
    pick(page, "a")
    key(page, "Control+BracketRight")
    expect_stack(page, "bacd")
    pick(page, "d")
    key(page, "Control+BracketRight")
    pick(page, "b")
    key(page, "Control+BracketLeft")
    pick(page, "c", "d")
    key(page, "Control+BracketRight")
    page.keyboard.press("Control+z")
    expect_stack(page, "abcd")


def test_meta_bracket_steps_on_a_mac(editor):
    page = editor(*boxes(*"abc"))
    pick(page, "a")
    key(page, "Meta+BracketRight")
    expect_stack(page, "bac")


def test_a_bracket_with_nothing_picked_steps_nothing(editor):
    page = editor(*boxes(*"abc"))
    page.locator(".sheet").first.click(position={"x": 5, "y": 5})
    expect(page.locator(".block.sel")).to_have_count(0)
    key(page, "Control+BracketRight")
    expect_stack(page, "abc")
    key(page, "Control+Shift+BracketLeft")
    expect_stack(page, "abc")
