"""Ctrl+B, Ctrl+I and Ctrl+U on a word, a selection and several blocks.

Shared pieces live in test_keys.py."""

import pytest
from playwright.sync_api import expect
from test_keys import (
    WORDS,
)
from ui import (
    FIELD,
    LINE,
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
    # Beside a word a colour is for what is typed next, though the colour's input takes the focus:
    # the block and its words keep theirs, and the input shows the new one.
    page.keyboard.press("End")
    expect(colour).to_have_value("#222222")
    # The press in the panel keeps the field open.
    colour.dispatch_event("pointerdown")
    colour.fill("#0000ff")
    expect(page.locator(f"{FIELD} span[data-color]")).to_have_text("Hallo")
    expect(at(page, "a").locator(".frame")).to_have_css("color", "rgb(34, 34, 34)")
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
