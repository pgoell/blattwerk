"""Cut, copy and paste: blocks that outlast the editor, and pictures from other apps."""

import re

import pytest
from playwright.sync_api import expect
from ui import (
    FIELD,
    LINE,
    RECT,
    RULING,
    TABLE,
    TEXT,
    angle,
    at,
    box,
    copy_picture,
    expect_picked,
    maths,
    mirror,
    pick,
    picture,
    png,
    saved,
    sheet,
    unpick,
    upload,
    user,
)

STAR = {"code": "2B50"}
REFUSED = "Das Bild ließ sich nicht hochladen"
# A paste of a file the server refuses, as the browser tells the page of one.
PASTE_BMP = """() => {
    const data = new DataTransfer();
    data.items.add(new File([new Uint8Array([66, 77])], "bild.bmp", { type: "image/bmp" }));
    const paste = { clipboardData: data, bubbles: true, cancelable: true };
    document.body.dispatchEvent(new ClipboardEvent("paste", paste));
}"""


def button(page, name):
    return page.get_by_role("button", name=name, exact=True).first


def blocks(page):
    return page.locator(".block")


def every(client):
    """One block of every type in two columns, the last two a group."""
    kinds = [
        ("text", TEXT),
        ("shape", RECT),
        ("shape", LINE),
        ("image", picture(upload(client))["props"]),
        ("table", TABLE),
        ("ruling", RULING),
        ("maths", maths(client)),
        ("symbol", STAR),
        ("text", {**TEXT, "text": "eins"}),
        ("shape", {**RECT, "fill": "#00ff00"}),
    ]
    return [
        box(
            f"b{i}",
            kind,
            props,
            z=i + 1,
            x=15 + 100 * (i % 2),
            y=20 + 30 * (i // 2),
            w=80,
            **({"group": ["g"]} if i > 7 else {}),
        )
        for i, (kind, props) in enumerate(kinds)
    ]


def stored(page, client):
    """The first page's blocks as the server holds them now, with no wait for a save."""
    sheet_id = page.url.rsplit("/", 1)[1]
    return client.get(f"/api/sheets/{sheet_id}").json()["doc"]["pages"][0]["blocks"]


def shapes(found):
    """What a copy keeps of each block, from back to front: all but its name and its place."""
    return [
        {"type": b["type"], "props": b["props"], "w": b["w"], "h": b["h"], "group": "group" in b}
        for b in sorted(found, key=lambda b: b["z"])
    ]


def places(found):
    return sorted((b["x"], b["y"]) for b in found)


def go(page, other, count):
    """Opens another sheet of the same user in this tab."""
    page.goto(f"{page.url.rsplit('/blatt/', 1)[0]}/blatt/{other['id']}")
    ready(page, count)


def ready(page, count):
    expect(page.locator('main.editor[data-ready="1"]')).to_be_visible()
    expect(blocks(page)).to_have_count(count)
    # The keys and the clipboard are for the tab with the focus.
    page.bring_to_front()
    unpick(page)


def all_of(page, count):
    unpick(page)
    page.keyboard.press("Control+a")
    expect(page.locator(".block.sel")).to_have_count(count)


def test_ctrl_x_cuts_every_block_type_and_a_paste_brings_it_back(editor):
    """A1"""
    client = user()
    page = editor(*every(client), client=client)
    before = shapes(stored(page, client))
    all_of(page, len(before))
    page.keyboard.press("Control+x")
    expect(blocks(page)).to_have_count(0)
    assert saved(page, client) == []
    page.keyboard.press("Control+v")
    expect(blocks(page)).to_have_count(len(before))
    assert shapes(saved(page, client)) == before


def test_one_undo_puts_the_cut_blocks_back(editor):
    """A2"""
    client = user()
    page = editor(
        box("a", "text", TEXT),
        box("b", "shape", RECT, z=2),
        box("c", "text", TEXT, z=3),
        client=client,
    )
    before = stored(page, client)
    pick(page, "a", "b")
    page.keyboard.press("Control+x")
    expect(blocks(page)).to_have_count(1)
    assert [b["id"] for b in saved(page, client)] == ["c"]
    page.keyboard.press("Control+z")
    expect(blocks(page)).to_have_count(3)
    assert sorted(saved(page, client), key=lambda b: b["z"]) == before


@pytest.mark.parametrize("touch", [False, True], ids=["mouse", "touch"])
def test_the_button_ausschneiden_cuts(editor, touch):
    """A3"""
    client = user()
    page = editor(box("a", "shape", RECT), box("b", "text", TEXT, z=2), client=client, touch=touch)

    def press(target):
        target.tap() if touch else target.click()

    cut = button(page, "Ausschneiden")
    assert cut.evaluate("el => el.nextElementSibling.getAttribute('aria-label')") == "Kopieren"
    press(at(page, "a"))
    expect_picked(page, "a")
    press(cut)
    expect(blocks(page)).to_have_count(1)
    expect(at(page, "b")).to_be_visible()
    press(button(page, "Einfügen"))
    expect(blocks(page)).to_have_count(2)
    assert shapes(saved(page, client))[-1]["props"] == RECT


def test_a_copy_of_every_block_type_lasts_over_a_reload(editor):
    """A4"""
    client = user()
    page = editor(*every(client), client=client)
    before = shapes(stored(page, client))
    all_of(page, len(before))
    page.keyboard.press("Control+c")
    page.reload()
    ready(page, len(before))
    page.keyboard.press("Control+v")
    expect(blocks(page)).to_have_count(2 * len(before))
    # The copies lie in front of the originals, in the same order.
    assert shapes(saved(page, client)) == before + before


def test_a_copy_pastes_into_another_sheet_at_the_originals_place(editor):
    """A5, I2"""
    client = user()
    page = editor(box("a", "shape", RECT, w=40), client=client)
    other = sheet(client, [box("t", "text", TEXT, z=3)])
    pick(page, "a")
    page.keyboard.press("Control+c")
    go(page, other, 1)
    page.keyboard.press("Control+v")
    expect(blocks(page)).to_have_count(2)
    expect(page.locator(".block.sel")).to_have_count(1)
    [pasted] = [b for b in saved(page, client) if b["id"] != "t"]
    assert (pasted["type"], pasted["props"]) == ("shape", RECT)
    assert (pasted["x"], pasted["y"]) == (15, 50)


def expect_picture(page, client, count):
    """Waits for a selected picture block that the server serves, among `count` blocks."""
    expect(blocks(page)).to_have_count(count)
    img = page.locator(".block.sel .picture img")
    expect(img).to_have_attribute("src", re.compile(r"/api/uploads/\d+$"))
    # The pasted picture is three pixels wide; one that failed to load has no width.
    expect(img).to_have_js_property("naturalWidth", 3)
    [held] = [b for b in saved(page, client) if b["type"] == "image"]
    # The clipboard writes the picture anew, so the bytes are a PNG but not the ones copied.
    served = client.get(f"/api/uploads/{held['props']['upload']}")
    assert served.headers["content-type"] == "image/png"
    assert served.content.startswith(png()[:8])


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
    # The block copied before the words is still the one a paste on the sheet gives.
    page.keyboard.press("Control+v")
    expect(blocks(page)).to_have_count(3)
    assert shapes(saved(page, client))[-1]["props"] == RECT


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


def test_a_cut_pastes_back_in_place_and_each_further_paste_steps_on(editor):
    """I2"""
    client = user()
    page = editor(box("a", "shape", RECT, w=40), client=client)
    pick(page, "a")
    page.keyboard.press("Control+x")
    expect(blocks(page)).to_have_count(0)
    for count, found in enumerate([[(15, 50)], [(15, 50), (20, 55)]], start=1):
        page.keyboard.press("Control+v")
        expect(blocks(page)).to_have_count(count)
        assert places(saved(page, client)) == found


def test_a_paste_beside_its_original_steps_aside(editor):
    """I2"""
    client = user()
    page = editor(box("a", "shape", RECT, w=40), client=client)
    pick(page, "a")
    page.keyboard.press("Control+c")
    for count, found in enumerate([[(15, 50), (20, 55)], [(15, 50), (20, 55), (25, 60)]], start=2):
        page.keyboard.press("Control+v")
        expect(blocks(page)).to_have_count(count)
        assert places(saved(page, client)) == found


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


def test_with_nothing_selected_cut_and_copy_leave_the_clipboard(editor):
    """I4"""
    client = user()
    page = editor(box("a", "shape", RECT), box("b", "text", TEXT, z=2), client=client)
    pick(page, "a")
    page.keyboard.press("Control+c")
    unpick(page)
    expect(button(page, "Ausschneiden")).to_be_disabled()
    page.keyboard.press("Control+x")
    page.keyboard.press("Control+c")
    expect(blocks(page)).to_have_count(2)
    page.keyboard.press("Control+v")
    expect(blocks(page)).to_have_count(3)
    assert shapes(saved(page, client))[-1]["props"] == RECT


def test_redo_cuts_again_and_the_clipboard_holds_the_cut(editor):
    """I5"""
    client = user()
    page = editor(box("a", "shape", RECT, w=40), client=client)
    pick(page, "a")
    page.keyboard.press("Control+x")
    expect(blocks(page)).to_have_count(0)
    page.keyboard.press("Control+z")
    expect(at(page, "a")).to_be_visible()
    page.keyboard.press("Control+y")
    expect(blocks(page)).to_have_count(0)
    page.keyboard.press("Control+z")
    expect(at(page, "a")).to_be_visible()
    page.keyboard.press("Control+v")
    expect(blocks(page)).to_have_count(2)
    assert places(saved(page, client)) == [(15, 50), (20, 55)]


def test_a_cut_keeps_the_order_and_the_group_and_the_paste_is_selected(editor):
    """I6"""
    client = user()
    group = {"group": ["g"]}
    # The order on the sheet is not the order in the document.
    page = editor(
        box("c", "shape", RECT, z=3),
        box("a", "text", TEXT),
        box("d", "shape", LINE, z=4, **group),
        box("b", "table", TABLE, z=2, **group),
        client=client,
    )
    before = shapes(stored(page, client))
    assert [b["type"] for b in before] == ["text", "table", "shape", "shape"]
    all_of(page, 4)
    page.keyboard.press("Control+x")
    expect(blocks(page)).to_have_count(0)
    page.keyboard.press("Control+v")
    expect(blocks(page)).to_have_count(4)
    expect(page.locator(".block.sel")).to_have_count(4)
    held = saved(page, client)
    assert shapes(held) == before
    table, line = (b for b in sorted(held, key=lambda b: b["z"]) if "group" in b)
    assert table["group"] == line["group"]
    unpick(page)
    at(page, line["id"]).click()
    expect_picked(page, table["id"], line["id"])


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


def test_a_refused_file_shows_the_alert_and_adds_nothing(editor):
    """I7"""
    page = editor(box("a", "text", TEXT))
    unpick(page)
    with page.expect_event("dialog") as info:
        page.evaluate(PASTE_BMP)
    assert info.value.message.startswith(REFUSED)
    info.value.accept()
    expect(blocks(page)).to_have_count(1)


def test_a_copy_pastes_in_another_tab_already_open(editor):
    """I8"""
    client = user()
    page = editor(box("a", "shape", RECT, w=40), client=client)
    other = sheet(client, [])
    tab = page.context.new_page()
    tab.goto(f"{page.url.rsplit('/blatt/', 1)[0]}/blatt/{other['id']}")
    ready(tab, 0)
    page.bring_to_front()
    pick(page, "a")
    page.keyboard.press("Control+c")
    tab.bring_to_front()
    unpick(tab)
    tab.keyboard.press("Control+v")
    expect(blocks(tab)).to_have_count(1)
    [pasted] = saved(tab, client)
    assert (pasted["type"], pasted["props"]) == ("shape", RECT)


@pytest.mark.parametrize(
    "junk", ["[{}]", '"abc"', '[{"id":"q","type":"text"}]', "null", "x{", "[null]"]
)
def test_a_clip_that_holds_no_whole_blocks_pastes_nothing(editor, junk):
    """A stored clip of another build, or of none, harms neither the editor nor the sheet."""
    page = editor(box("a", "shape", RECT, w=40))
    unpick(page)
    # The browser's clipboard outlives a test: a picture an earlier one left there would paste.
    page.evaluate("navigator.clipboard.writeText('x')")
    page.evaluate("(junk) => localStorage.setItem('clip', junk)", junk)
    page.keyboard.press("Control+v")
    # The next copy heals it.
    pick(page, "a")
    page.keyboard.press("Control+c")
    page.keyboard.press("Control+v")
    expect(blocks(page)).to_have_count(2)


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
