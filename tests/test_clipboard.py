"""Cut, copy and paste: blocks that outlast the editor, and pictures from other apps."""

import re

import pytest
from playwright.sync_api import expect
from ui import (
    BROWSER,
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
    copy_text,
    expect_picked,
    maths,
    mirror,
    pick,
    picture,
    png,
    saved,
    sheet,
    track_writes,
    unpick,
    upload,
    user,
    writes_landed,
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
# A browser that gives the page no leave to write the system clipboard.
REFUSE = "() => { navigator.clipboard.writeText = () => Promise.reject(new Error()); }"
# WebKit on Linux takes a picture written to the system clipboard and gives none back.
no_picture = pytest.mark.webkit_xfail(204, "WebKit's Einfügen reads no picture the clipboard holds")


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


@no_picture
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


def einfuegen(page, how):
    """A paste by the keys, by the toolbar's button or by the right-click menu of the empty page."""
    if how == "keys":
        page.keyboard.press("Control+v")
    elif how == "button":
        button(page, "Einfügen").click()
    else:
        page.locator(".sheet").first.click(position={"x": 5, "y": 5}, button="right")
        page.get_by_role("menuitem", name="Einfügen", exact=True).click()


def fresh(page, client, *old):
    """The one block the server holds beside the `old` ones."""
    [new] = [b for b in saved(page, client) if b["id"] not in old]
    return new


@pytest.mark.parametrize("how", ["keys", "button", "menu"])
@pytest.mark.parametrize("clip", ["blocks copied before", "no blocks copied"])
def test_words_from_another_app_paste_as_a_text_block(editor, clip, how):
    """#138: the newest copy wins, here the words."""
    client = user()
    page = editor(box("a", "shape", RECT, w=40), box("b", "text", TEXT, z=2), client=client)
    if clip == "blocks copied before":
        pick(page, "a", "b")
        track_writes(page)
        page.keyboard.press("Control+c")
        # The picture lands after the words: wait for every write, or a late one writes over the
        # other app's words (#764).
        writes_landed(page)
    else:
        assert page.evaluate("localStorage.getItem('clip')") is None
    copy_text(page, "Wort")
    einfuegen(page, how)
    expect(blocks(page)).to_have_count(3)
    new = fresh(page, client, "a", "b")
    assert (new["type"], new["props"]) == ("text", {**TEXT, "text": "Wort"})


@pytest.mark.parametrize("how", ["keys", "button", "menu"])
@pytest.mark.parametrize("kind", ["text", "shape"])
def test_blocks_copied_after_words_from_another_app_paste_as_blocks(editor, kind, how):
    """#138: the newest copy wins, here the blocks, with words of their own or with none."""
    client = user()
    props = TEXT if kind == "text" else RECT
    page = editor(box("a", kind, props, w=40), client=client)
    copy_text(page, "Wort")
    pick(page, "a")
    page.keyboard.press("Control+c")
    unpick(page)
    einfuegen(page, how)
    expect(blocks(page)).to_have_count(2)
    new = fresh(page, client, "a")
    assert (new["type"], new["props"]) == (kind, props)


def test_a_pasted_text_is_selected_and_one_undo_takes_it_away(editor):
    """#138"""
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    copy_text(page, "Wort")
    page.keyboard.press("Control+v")
    expect(blocks(page)).to_have_count(2)
    expect(page.locator(".block.sel")).to_have_text("Wort")
    # Selected, not opened: the next key is the sheet's.
    expect(page.locator(FIELD)).to_have_count(0)
    page.keyboard.press("Control+z")
    expect(blocks(page)).to_have_count(1)
    expect(at(page, "a")).to_be_visible()
    assert [b["id"] for b in saved(page, client)] == ["a"]


def test_lines_from_another_app_paste_as_the_paragraphs_of_one_text_that_grows(editor):
    """#138: Windows ends a line with two signs, and the box is as high as its words need."""
    client = user()
    page = editor(box("a", "shape", RECT, w=40), client=client)
    # Word ends a whole line with a break, which makes no empty last paragraph.
    copy_text(page, "eins\r\nzwei\ndrei\r\n")
    page.keyboard.press("Control+v")
    expect(blocks(page)).to_have_count(2)
    # A text with no formatting is drawn as one piece that breaks at each paragraph's end.
    assert page.locator(".block.sel p").evaluate("el => el.innerText") == "eins\nzwei\ndrei"
    new = fresh(page, client, "a")
    assert new["props"]["text"] == "eins\nzwei\ndrei"
    assert new["h"] > 12
    # The height came with the paste: one undo takes all of it away.
    page.keyboard.press("Control+z")
    expect(blocks(page)).to_have_count(1)


@pytest.mark.parametrize("kind", ["text", "table"])
def test_words_from_another_app_pasted_while_writing_stay_the_fields(editor, kind):
    """#138"""
    client = user()
    page = editor(box("a", kind, TEXT if kind == "text" else TABLE), client=client)
    copy_text(page, "Wort")
    pick(page, "a")
    # Enter opens the text, or the first cell, with all of it picked.
    page.keyboard.press("Enter")
    field = page.locator(FIELD if kind == "text" else ".block textarea:focus")
    expect(field).to_be_focused()
    page.keyboard.press("Control+v")
    (expect(field).to_have_text if kind == "text" else expect(field).to_have_value)("Wort")
    expect(blocks(page)).to_have_count(1)


# The copy's blocks now belong to another account, as after its logout without Abmelden.
OTHER_OWNER = """() => {
    const held = JSON.parse(localStorage.getItem("clip"));
    localStorage.setItem("clip", JSON.stringify({ ...held, owner: held.owner + 1 }));
}"""
# The copy's mark, as the editor sets it: the hash of the words, see frontend/src/clip.ts.
MARK = """(words) => {
    const hash = (words) => [...words].reduce((h, c) => (h * 33) ^ c.codePointAt(0), 5381) >>> 0;
    localStorage.setItem("copied", String(hash(words)));
}"""


def test_another_accounts_copy_pastes_nothing_into_a_field_outside_the_editor(editor):
    """#751: the account page's field takes none of it either."""
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    pick(page, "a")
    page.keyboard.press("Control+c")
    page.evaluate(OTHER_OWNER)
    page.goto(f"{page.url.rsplit('/blatt/', 1)[0]}/konto")
    field = page.locator("#key-name")
    field.click()
    page.keyboard.press("Control+v")
    page.keyboard.type("!")
    expect(field).to_have_value("!")


def test_another_accounts_copy_pastes_nothing_into_an_open_text(editor):
    client = user()
    target = box("b", "text", {**TEXT, "text": "Ziel"}, z=2)
    page = editor(box("a", "text", TEXT), target, client=client)
    pick(page, "a")
    page.keyboard.press("Control+c")
    page.evaluate(OTHER_OWNER)
    pick(page, "b")
    page.keyboard.press("Enter")
    expect(page.locator(FIELD)).to_be_focused()
    page.keyboard.press("End")
    page.keyboard.press("Control+v")
    page.keyboard.type("!")
    expect(page.locator(FIELD)).to_have_text("Ziel!")
    expect(blocks(page)).to_have_count(2)


@pytest.mark.parametrize("kind", ["cell", "list", "panel"])
def test_another_accounts_copy_pastes_nothing_into_a_field(editor, kind):
    client = user()
    shape = box("a", "table", TABLE) if kind == "cell" else box("a", "text", TEXT)
    page = editor(shape, client=client, theme="", words=["Hund"])
    # Words with a tab: a paste into a cell would spread them over the cells.
    copy_text(page, "Ge\theim")
    page.evaluate(MARK, "Ge\theim")
    if kind == "cell":
        pick(page, "a")
        page.keyboard.press("Enter")
        field = page.locator(".block textarea:focus")
    elif kind == "list":
        page.get_by_role("tab", name="Lernwörter").click()
        field = page.get_by_label("Lernwörter", exact=True)
    else:
        pick(page, "a")
        field = page.locator(".panel input.mm").first
    field.click()
    expect(field).to_be_focused()
    before = field.input_value()
    page.keyboard.press("End")
    page.keyboard.press("Control+v")
    page.keyboard.type("1")
    expect(field).to_have_value(before + "1")


@pytest.mark.skipif(BROWSER == "webkit", reason="WebKit on Linux grants the page no clipboard read")
def test_own_copy_still_pastes_its_words_into_an_open_text(editor):
    client = user()
    target = box("b", "text", {**TEXT, "text": "Ziel"}, z=2)
    page = editor(box("a", "text", TEXT), target, client=client)
    pick(page, "a")
    page.keyboard.press("Control+c")
    pick(page, "b")
    page.keyboard.press("Enter")
    expect(page.locator(FIELD)).to_be_focused()
    page.keyboard.press("End")
    page.keyboard.press("Control+v")
    expect(page.locator(FIELD)).to_have_text("ZielHallo")


def test_another_apps_words_still_paste_into_an_open_text_after_another_account(editor):
    client = user()
    target = box("b", "text", {**TEXT, "text": "Ziel"}, z=2)
    page = editor(box("a", "text", TEXT), target, client=client)
    pick(page, "a")
    track_writes(page)
    page.keyboard.press("Control+c")
    page.evaluate(OTHER_OWNER)
    # The copy's picture lands after its words, and a refused picture falls back to words: wait for
    # every write, or a late one writes over the other app's words.
    writes_landed(page)
    copy_text(page, "Wort")
    pick(page, "b")
    page.keyboard.press("Enter")
    expect(page.locator(FIELD)).to_be_focused()
    page.keyboard.press("End")
    page.keyboard.press("Control+v")
    expect(page.locator(FIELD)).to_have_text("ZielWort")


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


def test_a_refused_file_says_so_in_a_line_and_adds_nothing(editor):
    """I7"""
    page = editor(box("a", "text", TEXT))
    unpick(page)
    page.evaluate(PASTE_BMP)
    expect(page.locator(".notice.fault")).to_contain_text(REFUSED)
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
    # A blank, as a copy of blocks with no words leaves: words no copy of the editor's left there
    # would paste as a text block.
    page.evaluate("navigator.clipboard.writeText(' ')")
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


# The clipboard's items as the browser holds them, and the first picture's bytes in base64.
CLIPBOARD = """async () => {
    const items = await navigator.clipboard.read();
    const types = items.flatMap((item) => item.types).sort();
    const item = items.find((i) => i.types.includes("image/png"));
    if (!item) return { types, png: null };
    const bytes = new Uint8Array(await (await item.getType("image/png")).arrayBuffer());
    let text = "";
    for (const b of bytes) text += String.fromCharCode(b);
    return { types, png: btoa(text) };
}"""
# A PNG drawn back to pixels: its size, the red and blue pixels it has, and its top left pixel.
PIXELS = """async (b64) => {
    const bytes = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
    const bitmap = await createImageBitmap(new Blob([bytes], { type: "image/png" }));
    const canvas = new OffscreenCanvas(bitmap.width, bitmap.height);
    const ctx = canvas.getContext("2d");
    ctx.drawImage(bitmap, 0, 0);
    const { data } = ctx.getImageData(0, 0, bitmap.width, bitmap.height);
    let red = 0;
    let blue = 0;
    for (let i = 0; i < data.length; i += 4) {
        if (data[i + 3] === 0) continue;
        if (data[i] > 200 && data[i + 1] < 80 && data[i + 2] < 80) red++;
        if (data[i + 2] > 200 && data[i] < 80 && data[i + 1] < 80) blue++;
    }
    const corner = Array.from(data.slice(0, 4));
    return { width: bitmap.width, height: bitmap.height, red, blue, corner };
}"""
chromium_only = pytest.mark.skipif(
    BROWSER == "webkit", reason="WebKit on Linux grants the page no clipboard read"
)
KINDS = ["text", "shape", "line", "picture", "table", "ruling", "maths", "group"]


def one(kind, client):
    """One block of the kind, or two blocks in a group."""
    kinds = {
        "text": [box("a", "text", TEXT)],
        "shape": [box("a", "shape", RECT)],
        "line": [box("a", "shape", LINE)],
        "picture": [box("a", "image", picture(upload(client))["props"])],
        "table": [box("a", "table", TABLE)],
        "ruling": [box("a", "ruling", RULING)],
        "maths": [box("a", "maths", maths(client))],
        "group": [box("a", "shape", RECT, group=["g"]), box("b", "text", TEXT, z=2, group=["g"])],
    }
    return kinds[kind]


def clipboard_picture(page):
    """Waits for the copy's picture on the clipboard; gives its item types and its pixels."""
    # The write is async: five seconds at most.
    for _ in range(50):
        got = page.evaluate(CLIPBOARD)
        if got["png"] is not None:
            break
        page.wait_for_timeout(100)
    assert got["png"] is not None, f"no picture on the clipboard, only {got['types']}"
    return got["types"], page.evaluate(PIXELS, got["png"])


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
