"""A picture from another app pastes as a picture, and blocks copied after it paste as blocks."""

import base64

import pytest
from playwright.sync_api import expect
from test_clipboard import (
    HOLD_BLOBS,
    OTHER_APP,
    PASTE_BMP,
    REFUSE,
    REFUSED,
    blocks,
    button,
    expect_picture,
    places,
    shapes,
)
from ui import (
    BROWSER,
    FIELD,
    RECT,
    RULING,
    TABLE,
    TEXT,
    angle,
    at,
    box,
    copy_picture,
    mirror,
    pick,
    picture,
    png,
    saved,
    track_writes,
    unpick,
    upload,
    user,
    writes_landed,
)


def test_a_picture_from_another_app_pastes_as_a_picture_block(editor):
    """A6"""
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    copy_picture(page)
    page.keyboard.press("Control+v")
    expect_picture(page, client, 2)


def test_the_button_einfuegen_pastes_a_picture_by_touch(editor):
    """A7"""
    client = user()
    page = editor(box("a", "text", TEXT), client=client, touch=True)
    copy_picture(page)
    button(page, "Einfügen").tap()
    expect_picture(page, client, 2)


@pytest.mark.parametrize("kind", ["text", "table"])
def test_in_a_field_the_keys_work_on_the_words_alone(editor, kind):
    """I1"""
    client = user()
    props, word = (TEXT, "Hallo") if kind == "text" else (TABLE, "H")
    page = editor(box("a", "shape", RECT), box("b", kind, props, z=2), client=client)
    pick(page, "a")
    page.keyboard.press("Control+c")
    pick(page, "b")
    # Enter opens the text, or the first cell, with all of it picked.
    page.keyboard.press("Enter")
    field = page.locator(FIELD if kind == "text" else ".block textarea:focus")
    words = expect(field).to_have_text if kind == "text" else expect(field).to_have_value
    words(word)
    page.keyboard.press("Control+x")
    words("")
    expect(blocks(page)).to_have_count(2)
    page.keyboard.press("Control+v")
    words(word)
    page.keyboard.press("Control+a")
    page.keyboard.press("Control+c")
    page.keyboard.press("ArrowRight")
    page.keyboard.press("Control+v")
    words(word * 2)
    expect(blocks(page)).to_have_count(2)
    page.keyboard.press("Escape")
    unpick(page)
    # The words were copied after the block, so a paste on the sheet gives them, as a text block.
    page.keyboard.press("Control+v")
    expect(blocks(page)).to_have_count(3)
    pasted = shapes(saved(page, client))[-1]
    assert (pasted["type"], pasted["props"]["text"]) == ("text", word)


@pytest.mark.parametrize("kind", ["text", "table", "ruling"])
def test_a_picture_pasted_while_typing_lands_on_the_sheet(editor, kind):
    """The field has no place for a picture; its words stay as typed."""
    client = user()
    props = {"text": TEXT, "table": TABLE, "ruling": RULING}[kind]
    page = editor(box("a", kind, props), client=client)
    copy_picture(page)
    pick(page, "a")
    # Enter opens the text, the first cell or the Lineatur, with all of it picked.
    page.keyboard.press("Enter")
    field = page.locator(FIELD if kind == "text" else ".block textarea:focus")
    page.keyboard.type("du")
    (expect(field).to_have_text if kind == "text" else expect(field).to_have_value)("du")
    page.keyboard.press("Control+v")
    expect_picture(page, client, 2)
    expect(at(page, "a")).to_have_class("block")
    [held] = [b for b in saved(page, client) if b["id"] == "a"]
    if kind == "table":
        assert held["props"]["cells"] == [["du", "Z"], ["3", "7"]]
    else:
        assert held["props"]["text"] == "du"
    if kind == "text":
        expect(at(page, "a")).to_have_text("du")


def test_blocks_copied_after_a_picture_paste_as_blocks(editor):
    """I3"""
    client = user()
    page = editor(box("a", "shape", RECT, w=40), client=client)
    copy_picture(page)
    pick(page, "a")
    page.keyboard.press("Control+c")
    page.keyboard.press("Control+v")
    expect(blocks(page)).to_have_count(2)
    assert [b["type"] for b in saved(page, client)] == ["shape", "shape"]


def test_a_paste_right_after_a_copy_brings_the_blocks_and_not_an_older_picture(editor):
    """I3"""
    client = user()
    turned = {**picture(upload(client)), "id": "bild", "x": 75, "y": 60, "w": 60, "h": 40}
    page = editor({**turned, "angle": 45, "flipX": True}, client=client)
    copy_picture(page)
    # A system clipboard that has not caught up: the copy's words never land, so it still holds
    # the picture.
    page.evaluate("() => { navigator.clipboard.writeText = () => new Promise(() => {}); }")
    pick(page, "bild")
    page.keyboard.press("Control+c")
    page.keyboard.press("Control+v")
    expect(blocks(page)).to_have_count(2)
    for name in page.eval_on_selector_all(".block", "els => els.map((el) => el.dataset.id)"):
        assert angle(page, name) == 45
        assert mirror(page, name) == (-1, 1)


@pytest.mark.parametrize("paste", ["Control+v", "Einfügen"])
@pytest.mark.parametrize("copy", ["Control+c", "Control+x", "Kopieren", "Ausschneiden"])
def test_a_copy_the_browser_lets_no_one_write_still_wins_over_an_older_picture(editor, copy, paste):
    """#174"""
    client = user()
    page = editor(box("a", "shape", RECT, w=40), client=client)
    copy_picture(page)
    page.evaluate(REFUSE)
    pick(page, "a")
    count = 2 if copy in ("Control+c", "Kopieren") else 1
    for key in (copy, paste):
        page.keyboard.press(key) if "+" in key else button(page, key).click()
        expect(blocks(page)).to_have_count(count if key == paste else count - 1)
    assert [b["type"] for b in saved(page, client)] == ["shape"] * count


def test_a_picture_copied_after_blocks_pastes_as_a_picture(editor):
    """I3"""
    client = user()
    page = editor(box("a", "shape", RECT, w=40), client=client)
    pick(page, "a")
    page.keyboard.press("Control+c")
    copy_picture(page)
    page.keyboard.press("Control+v")
    expect_picture(page, client, 2)
    assert sorted(b["type"] for b in saved(page, client)) == ["image", "shape"]


@pytest.mark.skipif(
    BROWSER == "webkit",
    reason="WebKit on Linux refuses a clipboard write that is not the page's own",
)
def test_a_picture_copied_while_the_block_picture_is_drawn_stays_a_picture(editor):
    """#1011: a picture copied elsewhere while the block picture is drawn stays what a paste brings,
    and the late block picture does not replace it."""
    client = user()
    page = editor(box("a", "shape", RECT, w=40), client=client)
    track_writes(page)
    page.evaluate(HOLD_BLOBS)
    pick(page, "a")
    page.keyboard.press("Control+c")
    page.evaluate(OTHER_APP, base64.b64encode(png()).decode())
    page.keyboard.press("Control+v")
    expect_picture(page, client, 2)
    page.evaluate("window.releaseBlobs()")
    writes_landed(page)
    page.keyboard.press("Control+v")
    expect(blocks(page)).to_have_count(3)
    assert sorted(b["type"] for b in saved(page, client)) == ["image", "image", "shape"]


def test_a_pasted_picture_is_selected_and_one_undo_takes_it_away(editor):
    """I7"""
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    copy_picture(page)
    page.keyboard.press("Control+v")
    expect_picture(page, client, 2)
    expect(page.locator(".block.sel")).to_have_count(1)
    page.keyboard.press("Control+z")
    expect(blocks(page)).to_have_count(1)
    expect(at(page, "a")).to_be_visible()
    assert [b["id"] for b in saved(page, client)] == ["a"]


def test_a_refused_file_says_so_in_a_line_and_adds_nothing(editor):
    """I7"""
    page = editor(box("a", "text", TEXT))
    unpick(page)
    page.evaluate(PASTE_BMP)
    expect(page.locator(".notice.fault")).to_contain_text(REFUSED)
    expect(blocks(page)).to_have_count(1)


def test_two_presses_at_once_on_einfuegen_stack_no_copies(editor):
    """I2: a press while the first still reads the clipboard pastes nothing more."""
    client = user()
    page = editor(box("a", "shape", RECT, w=40), client=client)
    pick(page, "a")
    button(page, "Kopieren").click()
    button(page, "Einfügen").evaluate("(el) => (el.click(), el.click())")
    expect(blocks(page)).to_have_count(2)
    button(page, "Einfügen").click()
    expect(blocks(page)).to_have_count(3)
    assert places(saved(page, client)) == [(15, 50), (20, 55), (25, 60)]
