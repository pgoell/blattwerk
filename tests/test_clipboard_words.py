"""Words from another app paste as a text block, and another account's copy pastes nothing."""

import pytest
from playwright.sync_api import expect
from test_clipboard import (
    MARK,
    OTHER_OWNER,
    blocks,
    einfuegen,
    fresh,
    ready,
)
from ui import (
    BROWSER,
    FIELD,
    RECT,
    TABLE,
    TEXT,
    at,
    box,
    copy_text,
    pick,
    saved,
    sheet,
    track_writes,
    unpick,
    user,
    writes_landed,
)


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
    page.evaluate("(junk) => localStorage.setItem('clip', junk)", junk)
    page.keyboard.press("Control+v")
    # The next copy heals it.
    pick(page, "a")
    page.keyboard.press("Control+c")
    page.keyboard.press("Control+v")
    expect(blocks(page)).to_have_count(2)
