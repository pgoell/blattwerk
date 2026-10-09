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
    caret,
    expect_picked,
    pick,
    picked,
    picture,
    stopped,
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
    # Tab goes to the next cell, with the caret at the end of its text as before.
    page.keyboard.press("Tab")
    expect(cell).to_have_value("Z")
    page.keyboard.type("!")
    expect(cell).to_have_value("Z!")
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


def test_tab_goes_through_the_blocks_from_back_to_front(editor):
    # The order on the sheet is not the order in the document.
    page = editor(box("c", "text", TEXT, z=3), box("a", "text", TEXT), box("b", "shape", RECT, z=2))
    pick(page, "a")
    for name in ("b", "c", "a"):
        page.keyboard.press("Tab")
        expect_picked(page, name)
    for name in ("c", "b", "a"):
        page.keyboard.press("Shift+Tab")
        expect_picked(page, name)


def test_tab_stops_once_at_a_group(editor):
    group = {"group": ["g"]}
    page = editor(
        box("a", "text", TEXT),
        box("b", "text", TEXT, z=2, **group),
        box("c", "text", TEXT, z=3, **group),
        box("d", "text", TEXT, z=4),
    )
    pick(page, "a")
    for names in (["b", "c"], ["d"], ["a"]):
        page.keyboard.press("Tab")
        expect_picked(page, *names)
    for names in (["d"], ["b", "c"], ["a"]):
        page.keyboard.press("Shift+Tab")
        expect_picked(page, *names)


@pytest.mark.parametrize(
    "key, css, on, off",
    [
        ("b", "font-weight", "700", "400"),
        ("i", "font-style", "italic", "normal"),
        ("u", "text-decoration-line", "underline", "none"),
    ],
)
def test_ctrl_b_i_u_set_the_whole_of_a_selected_text(editor, key, css, on, off):
    page = editor(box("a", "text", TEXT))
    frame = at(page, "a").locator(".frame")
    pick(page, "a")
    expect(frame).to_have_css(css, off)
    page.keyboard.press(f"Control+{key}")
    expect(frame).to_have_css(css, on)
    # No field opened for it.
    assert page.locator(".ProseMirror").count() == 0
    page.keyboard.press("Control+z")
    expect(frame).to_have_css(css, off)
    assert picked(page) == ["a"]
    # The key made one step: redo brings it back, and one more undo leaves nothing to undo.
    page.keyboard.press("Control+y")
    expect(frame).to_have_css(css, on)
    page.keyboard.press("Control+z")
    expect(frame).to_have_css(css, off)
    expect(page.get_by_label("Rückgängig")).to_be_disabled()


def test_ctrl_i_in_a_field_sets_the_picked_words(editor):
    page = editor(box("a", "text", TEXT))
    pick(page, "a")
    page.keyboard.press("Enter")
    expect(page.locator(FIELD)).to_be_focused()
    italic = page.locator(f"{FIELD} span[data-italic]")
    page.keyboard.press("Control+a")
    page.keyboard.press("Control+i")
    expect(italic).to_have_text("Hallo")
    expect(italic).to_have_css("font-style", "italic")
    page.keyboard.press("Control+i")
    expect(italic).to_have_count(0)
    expect(page.locator(f"{FIELD} p")).to_have_css("font-style", "normal")
    expect(page.locator(FIELD)).to_be_focused()


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


def test_a_button_with_the_focus_keeps_enter_and_tab(editor):
    page = editor(box("a", "text", TEXT), box("b", "text", TEXT, z=2))
    pick(page, "a")
    bold = page.locator(".panel button.bold")
    bold.focus()
    page.keyboard.press("Tab")
    # The focus went on to the next button, and the selection stayed.
    expect(page.locator(".panel button.italic")).to_be_focused()
    assert picked(page) == ["a"]
    # Enter presses the button and opens no field.
    page.keyboard.press("Enter")
    expect(at(page, "a").locator(".frame")).to_have_css("font-style", "italic")
    assert page.locator(".ProseMirror").count() == 0
    assert picked(page) == ["a"]


def test_tab_with_nothing_selected_starts_at_the_back_or_the_front(editor):
    page = editor(box("c", "text", TEXT, z=3), box("a", "text", TEXT), box("b", "shape", RECT, z=2))
    page.keyboard.press("Tab")
    expect_picked(page, "a")
    unpick(page)
    page.keyboard.press("Shift+Tab")
    expect_picked(page, "c")
    # A button that has the focus keeps the key.
    unpick(page)
    page.get_by_label("Größer", exact=True).focus()
    page.keyboard.press("Shift+Tab")
    expect(page.get_by_label("Größer", exact=True)).not_to_be_focused()
    assert page.evaluate("document.activeElement.tagName") == "BUTTON"
    assert picked(page) == []


def test_tab_on_an_empty_page_stays_the_browsers(editor):
    page = editor()
    assert not stopped(page, "Tab")
    assert page.evaluate("document.activeElement !== document.body")


def test_tab_starts_at_a_group_as_a_whole(editor):
    group = {"group": ["g"]}
    page = editor(
        box("a", "text", TEXT, **group),
        box("b", "text", TEXT, z=2, **group),
        box("c", "text", TEXT, z=3),
    )
    page.keyboard.press("Tab")
    expect_picked(page, "a", "b")
    # Enter and F2 open nothing in a group.
    for key in ("Enter", "F2"):
        page.keyboard.press(key)
        assert page.locator(".ProseMirror").count() == 0
        assert picked(page) == ["a", "b"]


def test_tab_goes_on_from_the_front_most_of_several_and_stays_on_its_page(editor):
    names = ("a", "b", "c", "d")
    page = editor(
        *(box(name, "text", TEXT, z=z) for z, name in enumerate(names, 1)),
        more=[box("far", "text", TEXT)],
    )
    pick(page, "a", "c")
    page.keyboard.press("Tab")
    expect_picked(page, "d")
    # Past the front it starts over at the back of the same page.
    page.keyboard.press("Tab")
    expect_picked(page, "a")
    page.keyboard.press("Shift+Tab")
    expect_picked(page, "d")
    # The other page has its own round, of one block that stays selected.
    at(page, "far").click()
    expect_picked(page, "far")
    for key in ("Tab", "Shift+Tab"):
        assert stopped(page, key)
        assert picked(page) == ["far"]


def test_tab_ends_a_crop_and_goes_on(editor):
    client = user()
    page = editor(
        box("a", "text", TEXT), {**picture(upload(client)), "id": "bild", "z": 2}, client=client
    )
    at(page, "bild").dblclick()
    expect(page.locator(".crop")).to_have_count(1)
    page.keyboard.press("Tab")
    expect(page.locator(".crop")).to_have_count(0)
    expect_picked(page, "a")


def test_tab_in_a_field_moves_an_item_in(editor):
    page = editor(box("a", "text", ITEM), box("b", "text", TEXT, z=2))
    pick(page, "a")
    page.keyboard.press("Enter")
    page.keyboard.press("Tab")
    expect(page.locator(f"{FIELD} p")).to_have_attribute("data-level", "1")
    expect(page.locator(FIELD)).to_be_focused()
    assert picked(page) == ["a"]


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
        "name": ("name", {}),
        "points": ("points", {"max": 10}),
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


@pytest.mark.parametrize("word, offset", WORDS)
def test_ctrl_b_with_the_caret_in_a_word_sets_the_word(editor, word, offset):
    text = "Hallo liebe Grüße, Übung2 folgt: geht's geht\u2019s weiter-so 'gut' u\u0308ber"
    page = editor(box("a", "text", {**TEXT, "text": text}))
    bold = page.locator(f"{FIELD} span[data-bold]")
    caret(page, word, offset)
    page.keyboard.press("Control+b")
    expect(bold).to_have_text(word)
    expect(page.locator(".panel button.bold")).to_have_attribute("aria-pressed", "true")
    # The caret stayed where it was, and what is typed there is bold with its word.
    page.keyboard.type("x")
    expect(bold).to_have_text(f"{word[:offset]}x{word[offset:]}")
    # The same key takes it from the word again.
    page.keyboard.press("Control+b")
    expect(bold).to_have_count(0)
    expect(page.locator(".panel button.bold")).to_have_attribute("aria-pressed", "false")
    expect(page.locator(FIELD)).to_be_focused()


def test_undo_and_redo_of_a_words_look_while_typing(editor):
    page = editor(box("a", "text", TEXT))
    underlined = page.locator(f"{FIELD} span[data-underline]")
    caret(page, "Hallo", 2)
    page.keyboard.press("Control+u")
    expect(underlined).to_have_text("Hallo")
    for redo in ("Control+y", "Control+Shift+z"):
        page.keyboard.press("Control+z")
        expect(underlined).to_have_count(0)
        expect(page.locator(FIELD)).to_have_text("Hallo")
        page.keyboard.press(redo)
        expect(underlined).to_have_text("Hallo")
    expect(page.locator(FIELD)).to_be_focused()
    # The caret is still in the word.
    page.keyboard.type("x")
    expect(underlined).to_have_text("Haxllo")


def test_ctrl_b_beside_a_word_is_for_what_is_typed_next(editor):
    page = editor(box("a", "text", {**TEXT, "text": "Hallo du"}))
    bold = page.locator(f"{FIELD} span[data-bold]")
    button = page.locator(".panel button.bold")
    caret(page, "du", 2)
    page.keyboard.press("Control+b")
    expect(bold).to_have_count(0)
    expect(button).to_have_attribute("aria-pressed", "true")
    page.keyboard.type("x")
    expect(bold).to_have_text("x")
    page.keyboard.press("Control+b")
    expect(button).to_have_attribute("aria-pressed", "false")
    page.keyboard.type("y")
    expect(bold).to_have_text("x")
    expect(page.locator(FIELD)).to_have_text("Hallo duxy")
    # Before a word's first letter the caret is not in the word either.
    for _ in "duxy":
        page.keyboard.press("ArrowLeft")
    page.keyboard.press("Control+b")
    page.keyboard.type("z")
    expect(bold).to_have_text(["z", "x"])
    expect(page.locator(FIELD)).to_have_text("Hallo zduxy")


def test_ctrl_b_between_two_spaces_leaves_the_words_alone(editor):
    page = editor(box("a", "text", {**TEXT, "text": "Hallo  du"}))
    caret(page, "Hallo", 6)
    page.keyboard.press("Control+b")
    page.keyboard.type("x")
    expect(page.locator(f"{FIELD} span[data-bold]")).to_have_text("x")


def test_the_panel_sets_the_word_the_caret_is_in(editor):
    page = editor(box("a", "text", {**TEXT, "text": "Hallo du"}))
    colour = page.get_by_label("Farbe", exact=True)
    caret(page, "Hallo", 2)
    page.locator(".panel button.italic").click()
    expect(page.locator(f"{FIELD} span[data-italic]")).to_have_text("Hallo")
    expect(page.locator(FIELD)).to_be_focused()
    colour.fill("#ff0000")
    expect(page.locator(f"{FIELD} span[data-color]")).to_have_text("Hallo")
    # The input shows the colour of the word the caret is in, and of the words picked.
    expect(colour).to_have_value("#ff0000")
    at(page, "a").locator(".ProseMirror").click()
    page.keyboard.press("Home")
    page.keyboard.press("Shift+End")
    expect(colour).to_have_value("#ff0000")
    # The colour's input takes the focus, so beside a word no next letter is coloured: the block is,
    # and the input shows the block's colour there.
    page.keyboard.press("Home")
    expect(colour).to_have_value("#222222")
    colour.fill("#0000ff")
    expect(page.locator(f"{FIELD} span[data-color]")).to_have_count(0)
    expect(at(page, "a").locator(".frame")).to_have_css("color", "rgb(0, 0, 255)")
    expect(colour).to_have_value("#0000ff")


def test_a_bold_word_made_by_the_keys_is_saved(editor):
    client = user()
    page = editor(box("a", "text", {**TEXT, "text": "Hallo du"}), client=client)
    caret(page, "du", 1)
    page.keyboard.press("Control+b")
    expect(page.locator(f"{FIELD} span[data-bold]")).to_have_text("du")
    page.keyboard.press("Escape")
    # The sheet draws the word as the field did.
    expect(at(page, "a").locator(".frame span").filter(has_text="du")).to_have_css(
        "font-weight", "700"
    )
    # The editor saves two seconds after the last change.
    expect(page.locator("header [role=status]")).to_have_text("Gespeichert", timeout=5000)
    saved = client.get(f"/api/sheets/{page.url.rsplit('/', 1)[1]}").json()
    assert saved["doc"]["pages"][0]["blocks"][0]["props"]["rich"] == [
        {"runs": [{"text": "Hallo "}, {"text": "du", "bold": True}]}
    ]


def test_ctrl_b_i_u_never_reach_the_browser_with_a_block_selected(editor):
    client = user()
    page = editor(
        box("lines", "ruling", RULING),
        box("table", "table", TABLE, z=2),
        box("line", "shape", LINE, z=3),
        {**picture(upload(client)), "id": "bild", "z": 4},
        client=client,
    )
    keys = ("Control+b", "Control+i", "Control+u")
    assert not any(stopped(page, key) for key in keys)
    for name in ("bild", "line"):
        unpick(page)
        at(page, name).click(force=True)
        expect_picked(page, name)
        assert all(stopped(page, key) for key in keys)
    # While typing in a ruling or in a cell the keys do nothing at all.
    for name, text in (("lines", ""), ("table", "H")):
        pick(page, name)
        page.keyboard.press("Enter")
        page.keyboard.press("End")
        area = at(page, name).locator("textarea")
        expect(area).to_be_focused()
        assert all(stopped(page, key) for key in keys)
        expect(area).to_have_value(text)
        expect(area).to_be_focused()
        page.keyboard.press("Escape")
    # In the title they are the browser's.
    page.get_by_label("Titel").focus()
    assert picked(page) == ["table"]
    assert not any(stopped(page, key) for key in keys)


def test_a_press_on_the_sheet_takes_the_focus_from_an_input(editor):
    page = editor(box("a", "text", TEXT), box("b", "text", TEXT, z=2))
    title = page.get_by_label("Titel")
    for key in ("Tab", "Enter"):
        title.click()
        expect(title).to_be_focused()
        pick(page, "a")
        expect(title).not_to_be_focused()
        page.keyboard.press(key)
        # Tab goes on to the next block, and Enter opens the one pressed.
        expect_picked(page, "b" if key == "Tab" else "a")
    expect(page.locator(FIELD)).to_be_focused()
    # A field that is open keeps the focus when its own block is pressed.
    at(page, "a").locator(".ProseMirror").click()
    expect(page.locator(FIELD)).to_be_focused()


def test_a_button_pressed_with_the_mouse_takes_no_focus(editor):
    page = editor(box("a", "text", TEXT), box("b", "text", TEXT, z=2))
    pick(page, "a")
    for label in ("Sperren", "Entsperren", "Größer", "Schrift größer", "Rechteck", "Rückgängig"):
        page.get_by_label(label, exact=True).click()
        assert page.evaluate("document.activeElement === document.body")
    expect(page.locator(".block")).to_have_count(2)
    expect(at(page, "a").locator(".frame")).to_have_css("font-size", "21.3333px")
    pick(page, "a")
    page.keyboard.press("Tab")
    expect_picked(page, "b")
    # Enter opens the copy that Duplizieren made and makes no other.
    page.get_by_label("Duplizieren", exact=True).click()
    expect(page.locator(".block")).to_have_count(3)
    page.keyboard.press("Enter")
    expect(page.locator(FIELD)).to_be_focused()
    expect(page.locator(".block")).to_have_count(3)
    assert picked(page) != ["b"]


def test_a_button_reached_by_the_keys_keeps_the_focus(editor):
    page = editor(box("a", "text", TEXT))
    pick(page, "a")
    copy = page.get_by_label("Duplizieren", exact=True)
    copy.focus()
    for count in (2, 3):
        page.keyboard.press("Enter")
        expect(page.locator(".block")).to_have_count(count)
        expect(copy).to_be_focused()
    assert page.locator(".ProseMirror").count() == 0


def test_a_button_ends_or_keeps_a_field_as_before(editor):
    page = editor(box("a", "text", TEXT), box("lines", "ruling", RULING, z=2))
    pick(page, "a")
    page.keyboard.press("Enter")
    # The panel's bold leaves the focus in the field, and its other buttons leave the field open.
    page.locator(".panel button.bold").click()
    expect(page.locator(FIELD)).to_be_focused()
    page.get_by_label("Schrift größer").click()
    expect(page.locator(FIELD)).not_to_be_focused()
    # A button of the bar ends it.
    at(page, "a").locator(".ProseMirror").click()
    expect(page.locator(FIELD)).to_be_focused()
    page.get_by_label("Größer", exact=True).click()
    expect(page.locator(".ProseMirror")).to_have_count(0)
    assert picked(page) == ["a"]
    pick(page, "lines")
    page.keyboard.press("Enter")
    written = at(page, "lines").locator("textarea.written")
    expect(written).to_be_editable()
    page.get_by_label("Größer", exact=True).click()
    expect(written).not_to_be_editable()


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


@pytest.mark.parametrize(
    "names", [["on", "off"], ["off", "on"], ["on", "too"], ["off", "on", "bild"]]
)
def test_ctrl_b_on_several_blocks_does_what_the_panels_button_does(editor, names):
    client = user()
    blocks = {
        "on": box("on", "text", {**TEXT, "bold": True}),
        "too": box("too", "text", {**TEXT, "bold": True}, z=2),
        "off": box("off", "text", TEXT, z=2),
        "bild": {**picture(upload(client)), "id": "bild", "z": 3},
    }
    page = editor(*(blocks[name] for name in names), client=client)
    frames = [at(page, name).locator(".frame") for name in names[:2]]
    button = page.locator(".panel button.bold")
    unpick(page)
    for name in names:
        at(page, name).click(modifiers=["Shift"], force=True)
    expect_picked(page, *names)
    # As in PowerPoint: bold goes off when every text has it, and else on for all. The button shows
    # as pressed only when all have it.
    every = "off" not in names
    for press in (lambda: page.keyboard.press("Control+b"), button.click):
        expect(button).to_have_attribute("aria-pressed", str(every).lower())
        press()
        for frame in frames:
            expect(frame).to_have_css("font-weight", "400" if every else "700")
        expect(button).to_have_attribute("aria-pressed", str(not every).lower())
        page.keyboard.press("Control+z")


def test_a_button_in_a_dialog_keeps_the_focus_in_it(editor):
    page = editor(box("a", "text", TEXT), box("b", "text", TEXT, z=2))
    pick(page, "a")
    page.get_by_label("Feedback").click()
    dialog = page.locator("dialog.feedback")
    # With nothing to send the form stays open and says so.
    dialog.get_by_text("Abschicken").click()
    expect(dialog.get_by_role("status")).not_to_be_empty()
    expect(dialog.get_by_text("Abschicken")).to_be_focused()
    # The keys are the dialog's, not the sheet's behind it, wherever in it the focus is.
    for _ in range(2):
        page.keyboard.press("Delete")
        page.keyboard.press("Tab")
        assert page.locator(".block").count() == 2
        assert picked(page) == ["a"]
        # A press on its heading leaves no control of it with the focus.
        dialog.locator("h1").click()
    page.keyboard.press("Escape")
    expect(dialog).to_have_count(0)


def test_a_right_click_on_a_button_leaves_the_focus(editor):
    page = editor(box("a", "text", TEXT))
    title = page.get_by_label("Titel")
    title.click()
    page.get_by_label("Größer", exact=True).click(button="right")
    expect(title).to_be_focused()


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


def test_ctrl_b_i_u_with_shift_or_alt_stay_the_browsers(editor):
    page = editor(box("a", "text", TEXT))
    pick(page, "a")
    # With Shift the browser names the capital letter.
    keys = [
        f"Control+{more}" for more in ("Shift+B", "Shift+I", "Shift+U", "Alt+b", "Alt+i", "Alt+u")
    ]
    assert not any(stopped(page, key) for key in keys)
    page.keyboard.press("Enter")
    expect(page.locator(FIELD)).to_be_focused()
    assert not any(stopped(page, key) for key in keys)
    expect(page.locator(f"{FIELD} span")).to_have_count(0)
    page.keyboard.press("Escape")
    for css, off in (("font-weight", "400"), ("font-style", "normal")):
        expect(at(page, "a").locator(".frame")).to_have_css(css, off)
    expect(at(page, "a").locator(".frame")).to_have_css("text-decoration-line", "none")
