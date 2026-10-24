"""The editor's keys, pressed in Chromium on the built frontend."""

import pytest
from playwright.sync_api import expect
from ui import (
    FIELD,
    ITEM,
    LINE,
    MATHS,
    RECT,
    RULING,
    TABLE,
    TEXT,
    at,
    box,
    expect_picked,
    pick,
    picked,
    picture,
    unpick,
    upload,
    user,
)


@pytest.mark.parametrize("key", ["Enter", "F2"])
@pytest.mark.parametrize("kind, props", [("text", TEXT), ("shape", RECT)])
def test_enter_and_f2_open_a_text_with_all_of_it_picked(editor, key, kind, props):
    page = editor(box("a", kind, props))
    pick(page, "a")
    page.keyboard.press(key)
    expect(page.locator(FIELD)).to_be_focused()
    # An arrow takes the caret to the end of what was picked.
    page.keyboard.press("ArrowRight")
    page.keyboard.type("!")
    expect(page.locator(FIELD)).to_have_text(f"{props.get('text', '')}!")
    # F2 goes back to the block, and the same key into its text again: typing replaces all.
    page.keyboard.press("F2")
    expect(page.locator(".ProseMirror")).to_have_count(0)
    assert picked(page) == ["a"]
    page.keyboard.press(key)
    page.keyboard.type("du")
    expect(page.locator(FIELD)).to_have_text("du")


def test_a_double_click_picks_no_text(editor):
    page = editor(box("a", "text", TEXT), box("lines", "ruling", {**RULING, "text": "abc"}, z=2))
    at(page, "a").dblclick()
    expect(page.locator(FIELD)).to_be_focused()
    page.keyboard.type("!")
    expect(page.locator(FIELD)).to_have_text("Hallo!")
    at(page, "lines").dblclick()
    written = at(page, "lines").locator("textarea.written")
    expect(written).to_be_focused()
    page.keyboard.type("!")
    expect(written).to_have_value("abc!")


def test_typing_over_an_item_keeps_its_list(editor):
    page = editor(box("a", "text", ITEM))
    pick(page, "a")
    page.keyboard.press("Enter")
    page.keyboard.type("zwei")
    expect(page.locator(f"{FIELD} p[data-list=bullet]")).to_have_text("zwei")


def test_enter_and_f2_pick_all_of_a_ruling_and_of_a_cell(editor):
    page = editor(
        box("lines", "ruling", {**RULING, "text": "abc"}), box("table", "table", TABLE, z=2)
    )
    written = at(page, "lines").locator("textarea.written")
    cell = at(page, "table").locator("textarea")
    pick(page, "lines")
    page.keyboard.press("F2")
    expect(written).to_be_focused()
    page.keyboard.type("x")
    expect(written).to_have_value("x")
    # F2 leaves the ruling and keeps the block.
    page.keyboard.press("F2")
    expect(written).not_to_be_editable()
    assert picked(page) == ["lines"]
    page.keyboard.press("F2")
    page.keyboard.type("y")
    expect(written).to_have_value("y")

    pick(page, "table")
    page.keyboard.press("Enter")
    expect(cell).to_be_focused()
    page.keyboard.type("x")
    expect(cell).to_have_value("x")
    # Tab goes to the next cell and picks its text, as PowerPoint does (#104).
    page.keyboard.press("Tab")
    expect(cell).to_have_value("Z")
    page.keyboard.type("!")
    expect(cell).to_have_value("!")
    page.keyboard.press("F2")
    expect(cell).to_have_count(0)
    assert picked(page) == ["table"]
    page.keyboard.press("F2")
    page.keyboard.type("y")
    expect(cell).to_have_value("y")


def test_enter_opens_a_ruling_and_a_table(editor):
    page = editor(box("lines", "ruling", RULING), box("table", "table", TABLE, z=2))
    written = at(page, "lines").locator("textarea.written")
    expect(written).not_to_be_editable()
    pick(page, "lines")
    page.keyboard.press("Enter")
    expect(written).to_be_editable()
    expect(written).to_be_focused()
    page.keyboard.type("abc")
    expect(written).to_have_value("abc")

    pick(page, "table")
    page.keyboard.press("Enter")
    expect(at(page, "table").locator("textarea")).to_be_focused()
    # The first cell is the one that opens.
    expect(at(page, "table").locator("textarea")).to_have_value("H")


def test_enter_leaves_a_picture_and_a_selection_of_two_alone(editor):
    client = user()
    page = editor(
        box("a", "text", TEXT),
        box("b", "text", TEXT, z=2),
        {**picture(upload(client)), "id": "bild", "z": 3},
        client=client,
    )
    opened = page.locator(".ProseMirror, .block textarea:not([readonly]), .crop")
    for names in (["bild"], ["a", "b"]):
        pick(page, *names)
        for key in ("Enter", "F2"):
            page.keyboard.press(key)
            # React has drawn what a key changed by the time the press returns.
            assert opened.count() == 0
            assert picked(page) == names
    # A double click does crop the picture, so the check above would have seen it.
    at(page, "bild").dblclick()
    expect(page.locator(".crop")).to_have_count(1)


def test_enter_in_a_field_makes_a_paragraph(editor):
    page = editor(box("a", "text", TEXT))
    pick(page, "a")
    page.keyboard.press("Enter")
    expect(page.locator(FIELD)).to_be_focused()
    page.keyboard.press("End")
    page.keyboard.press("Enter")
    page.keyboard.type("du")
    expect(page.locator(f"{FIELD} p")).to_have_text(["Hallo", "du"])
    expect(page.locator(FIELD)).to_be_focused()


def test_escape_leaves_the_field_and_keeps_the_block(editor):
    page = editor(box("a", "text", TEXT), box("b", "text", TEXT, z=2))
    pick(page, "a")
    page.keyboard.press("Enter")
    expect(page.locator(FIELD)).to_be_focused()
    page.keyboard.press("End")
    page.keyboard.type("!")
    page.keyboard.press("Escape")
    expect(page.locator(".ProseMirror")).to_have_count(0)
    expect(at(page, "a").locator(".frame")).to_have_text("Hallo!")
    assert picked(page) == ["a"]
    # Tab right after goes on to the next block.
    page.keyboard.press("Tab")
    expect_picked(page, "b")


def test_enter_and_f2_leave_what_holds_no_text_alone(editor):
    client = user()
    # A maths block as the editor makes it.
    limits = {
        **MATHS,
        "a": [[0, 9], [0, 9]],
        "b": [[0, 9], [0, 9]],
        "carry": "either",
        "rest": False,
        "format": "row",
    }
    maths = {**limits, **client.post("/api/maths", json=limits).json(), "columns": 3, "size": 14}
    kinds = {
        "locked": ("text", TEXT),
        "line": ("shape", LINE),
        "symbol": ("symbol", {"code": "270F"}),
        "maths": ("maths", maths),
    }
    page = editor(
        *(
            box(name, kind, props, z=z, locked=name == "locked")
            for z, (name, (kind, props)) in enumerate(kinds.items())
        ),
        client=client,
    )
    errors = []
    page.on("pageerror", lambda error: errors.append(error))
    page.on("console", lambda said: said.type == "error" and errors.append(said.text))
    opened = page.locator(".ProseMirror, .block textarea:not([readonly]), .crop")
    for name in kinds:
        unpick(page)
        at(page, name).click()
        expect_picked(page, name)
        for key in ("Enter", "F2"):
            page.keyboard.press(key)
            assert opened.count() == 0
            assert picked(page) == [name]
    assert errors == []


# A word holds an apostrophe between two letters, and the marks that combine with a letter. A hyphen
# ends it, and so does a quote at its edge.
WORDS = [
    ("Hallo", 2),
    ("Grüße", 3),
    ("Übung2", 1),
    ("geht's", 5),
    ("geht\u2019s", 2),
    ("weiter", 3),
    ("gut", 1),
    ("u\u0308ber", 2),
]


def test_enter_opens_a_block_just_added_and_tab_goes_on(editor):
    page = editor(box("a", "text", TEXT))
    page.get_by_label("Tabelle").click()
    expect(page.locator(".block")).to_have_count(2)
    page.keyboard.press("Enter")
    expect(page.locator(".block.sel textarea")).to_be_focused()
    expect(page.locator(".block")).to_have_count(2)
    page.keyboard.press("Escape")
    page.get_by_label("Rechteck").click()
    expect(page.locator(".block")).to_have_count(3)
    page.keyboard.press("Tab")
    expect_picked(page, "a")
    expect(page.locator(".block")).to_have_count(3)
    # A new text opens by itself.
    page.get_by_label("Text", exact=True).click()
    expect(page.locator(FIELD)).to_be_focused()


def test_home_right_after_enter_puts_the_caret_before_the_text(editor):
    page = editor(box("a", "text", TEXT))
    pick(page, "a")
    for key in ("Home", "ArrowLeft"):
        page.keyboard.press("Enter")
        page.keyboard.press(key)
        page.keyboard.type("x")
        expect(page.locator(FIELD)).to_have_text("xHallo")
        page.keyboard.press("Escape")
        page.keyboard.press("Control+z")
        expect(at(page, "a").locator(".frame")).to_have_text("Hallo")


def test_enter_opens_nothing_with_a_locked_block_selected_too(editor):
    client = user()
    page = editor(
        {**picture(upload(client)), "id": "bild", "z": 1, "locked": True},
        box("a", "text", TEXT, z=2),
        box("fest", "text", TEXT, z=3, locked=True),
        client=client,
    )
    errors = []
    page.on("pageerror", lambda error: errors.append(error))
    for names in (["bild", "a"], ["fest"]):
        unpick(page)
        for name in names:
            at(page, name).click(modifiers=["Shift"], force=True)
        expect_picked(page, *names)
        for key in ("Enter", "F2"):
            page.keyboard.press(key)
            assert page.locator(".ProseMirror").count() == 0
            assert picked(page) == names
    assert errors == []
