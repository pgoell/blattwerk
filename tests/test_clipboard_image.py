"""Copying blocks also puts a picture of them on the system clipboard."""

import pytest
from playwright.sync_api import expect
from test_clipboard import (
    CLIPBOARD,
    KINDS,
    all_of,
    blocks,
    button,
    chromium_only,
    clipboard_picture,
    one,
)
from ui import (
    FIELD,
    RECT,
    TEXT,
    box,
    copy_picture,
    pick,
    picture,
    saved,
    unpick,
    upload,
    user,
)


@chromium_only
def test_an_editor_starts_with_an_empty_clipboard(editor):
    """A picture one editor leaves is not there when the next one opens."""
    page = editor(box("a", "text", TEXT))
    copy_picture(page)
    again = editor(box("b", "text", TEXT))
    held = again.evaluate(
        """async () => {
            const items = await navigator.clipboard.read();
            const types = items.flatMap((item) => item.types);
            let text = "";
            for (const item of items) {
                if (item.types.includes("text/plain")) text += await (await item.getType("text/plain")).text();
            }
            return { types, text };
        }"""
    )
    assert [kind for kind in held["types"] if kind.startswith("image/")] == []
    assert held["text"].strip() == ""


@chromium_only
@pytest.mark.parametrize("kind", KINDS)
def test_every_block_type_copied_puts_a_picture_on_the_clipboard(editor, kind):
    """B1"""
    client = user()
    blocks_ = one(kind, client)
    page = editor(*blocks_, client=client)
    all_of(page, len(blocks_))
    page.keyboard.press("Control+c")
    types, pixels = clipboard_picture(page)
    assert types == ["image/png", "text/plain"]
    assert pixels["width"] > 0 and pixels["height"] > 0


@chromium_only
@pytest.mark.parametrize("how", ["Control+c", "Control+x", "Kopieren", "Ausschneiden"])
def test_copy_cut_and_their_buttons_all_put_the_picture_on_the_clipboard(editor, how):
    """B1: the keys and the buttons."""
    client = user()
    page = editor(box("a", "shape", RECT), client=client)
    pick(page, "a")
    if how.startswith("Control"):
        page.keyboard.press(how)
    else:
        button(page, how).click()
    types, _ = clipboard_picture(page)
    assert types == ["image/png", "text/plain"]


@chromium_only
def test_a_paste_here_of_the_copy_brings_the_blocks_not_a_picture(editor):
    """B2"""
    client = user()
    page = editor(box("a", "shape", RECT), client=client)
    pick(page, "a")
    page.keyboard.press("Control+c")
    clipboard_picture(page)
    page.keyboard.press("Control+v")
    expect(blocks(page)).to_have_count(2)
    # The button reads the system's clipboard, picture and words: it brings the blocks too.
    button(page, "Einfügen").click()
    expect(blocks(page)).to_have_count(3)
    assert sorted(b["type"] for b in saved(page, client)) == ["shape"] * 3


@chromium_only
def test_the_picture_shows_the_copied_blocks_alone(editor):
    """B3: block b, blue, lies over a and must not show."""
    client = user()
    page = editor(
        box("a", "shape", {**RECT, "fill": "#ff0000"}, z=1, x=15, y=20, w=80, h=20),
        box("b", "shape", {**RECT, "fill": "#0000ff"}, z=2, x=60, y=30, w=80, h=20),
        client=client,
    )
    pick(page, "a")
    page.keyboard.press("Control+c")
    types, pixels = clipboard_picture(page)
    assert types == ["image/png", "text/plain"]
    assert pixels["blue"] == 0
    assert pixels["red"] > 0


@chromium_only
def test_several_blocks_make_one_picture_cropped_to_their_hull(editor):
    """B4 and B5: the hull is 145 by 60 mm, with 1 mm all round, drawn at 4 px per mm."""
    client = user()
    page = editor(
        box("a", "shape", RECT, x=15, y=20, w=80, h=20),
        box("b", "shape", RECT, z=2, x=120, y=60, w=40, h=20),
        client=client,
    )
    pick(page, "a", "b")
    page.keyboard.press("Control+c")
    _, pixels = clipboard_picture(page)
    assert abs(pixels["width"] - 147 * 4) <= 2
    assert abs(pixels["height"] - 62 * 4) <= 2
    # Zoomed in, the picture is the same size. The first one goes, so the second is a new one.
    page.evaluate("navigator.clipboard.writeText('anders')")
    page.keyboard.press("Control+Equal")
    page.keyboard.press("Control+Equal")
    page.keyboard.press("Control+c")
    _, zoomed = clipboard_picture(page)
    assert (zoomed["width"], zoomed["height"]) == (pixels["width"], pixels["height"])


@chromium_only
def test_a_turned_block_shows_turned_in_the_picture(editor):
    """B8: a 40 by 20 mm rectangle turned 45 degrees is 42 mm wide; its top left corner is empty."""
    client = user()
    page = editor(
        box("a", "shape", {**RECT, "fill": "#ff0000"}, x=40, y=40, w=40, h=20, angle=45),
        client=client,
    )
    pick(page, "a")
    page.keyboard.press("Control+c")
    _, pixels = clipboard_picture(page)
    assert pixels["width"] > 40 * 4 + 4
    assert not (pixels["corner"][0] > 200 and pixels["corner"][1] < 80)


@chromium_only
def test_words_copied_in_an_open_text_stay_the_field_s_no_picture(editor):
    """B7"""
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    pick(page, "a")
    page.keyboard.press("Enter")
    expect(page.locator(FIELD)).to_have_text("Hallo")
    page.keyboard.press("Control+a")
    page.keyboard.press("Control+c")
    page.wait_for_timeout(300)
    types = page.evaluate(CLIPBOARD)["types"]
    assert "image/png" not in types


@chromium_only
def test_a_second_copy_while_the_first_ones_picture_is_drawn_wins(editor):
    """The picture of the first may come later than the second's: the clipboard holds the second."""
    client = user()
    page = editor(
        box("bild", "image", picture(upload(client))["props"]),
        box("t", "text", {**TEXT, "text": "zweite"}, z=2),
        client=client,
    )
    pick(page, "bild")
    page.keyboard.press("Control+c")
    pick(page, "t")
    page.keyboard.press("Control+c")
    clipboard_picture(page)
    page.wait_for_function("async () => (await navigator.clipboard.readText()) === 'zweite'")
    # The first one's write, if it lands, would show here.
    page.wait_for_timeout(1000)
    assert page.evaluate("navigator.clipboard.readText()") == "zweite"
    unpick(page)
    page.keyboard.press("Control+v")
    expect(blocks(page)).to_have_count(3)
    assert sorted(b["type"] for b in saved(page, client)) == ["image", "text", "text"]
