"""Words copied in a field, a table cell or the login page do not outlast the account."""

import pytest
from playwright.sync_api import expect
from test_clipboard import (
    blocks,
    button,
    chromium_only,
    ready,
    stored,
)
from test_clipboard_account import (
    CELLS,
    GAPPED,
    copy_in_text,
    copy_key,
    in_b_sheet,
    login,
    logout,
    next_list_paste_nothing,
    open_list,
    origin,
    own,
    someone,
    the_text_box,
)
from ui import (
    PASSWORD,
    RECT,
    TEXT,
    at,
    box,
    pick,
    saved,
    sheet,
    unpick,
    user,
)


@pytest.mark.parametrize("by", ["keys", "button"])
def test_words_copied_in_an_open_text_paste_nothing_for_the_next_account(editor, by):
    """#757: the words of a copy in an open text stay on the system's clipboard after the logout."""
    a = user()
    page = editor(the_text_box(), client=a)
    copy_in_text(page)
    logout(page)
    b, email = someone()
    login(page, email, sheet(b, [box("x", "shape", RECT, w=40)]), 1)
    before = stored(page, b)
    if by == "keys":
        field = open_list(page)
        field.press("Control+v")
        expect(field).to_have_value("")
    else:
        button(page, "Einfügen").click()
    expect(blocks(page)).to_have_count(1)
    assert stored(page, b) == before
    # A paste still on its way, as the button's is while it reads the clipboard, would show here.
    assert [b["type"] for b in own(page, b, 2)] == ["shape", "shape"]


@chromium_only
def test_abmelden_empties_the_clipboard_of_words_copied_in_an_open_text(editor):
    a = user()
    page = editor(the_text_box(), client=a)
    copy_in_text(page)
    logout(page)
    assert page.evaluate("navigator.clipboard.readText()") == ""


def test_the_same_account_after_a_new_login_pastes_no_words_of_an_open_text(editor):
    a, email = someone()
    page = editor(the_text_box(), client=a)
    mine = {"id": page.url.rsplit("/", 1)[1]}
    copy_in_text(page)
    logout(page)
    login(page, email, mine, 1)
    assert a.post("/api/login", json={"email": email, "password": PASSWORD}).status_code == 200
    before = stored(page, a)
    page.keyboard.press("Control+v")
    expect(blocks(page)).to_have_count(1)
    assert stored(page, a) == before


def test_the_same_session_pastes_its_own_words_of_an_open_text_into_a_field(editor):
    a = user()
    page = editor(the_text_box(), client=a)
    copy_in_text(page)
    field = open_list(page)
    field.press("Control+v")
    expect(field).not_to_have_value("")
    assert "Hund" in field.input_value()


def test_the_same_session_pastes_its_own_words_of_an_open_text_on_the_sheet_as_a_text(editor):
    """Outside a field the words make a text block, as words copied elsewhere do."""
    a = user()
    page = editor(the_text_box(), client=a)
    copy_in_text(page)
    unpick(page)
    page.keyboard.press("Control+v")
    expect(blocks(page)).to_have_count(2)
    [new] = [b for b in saved(page, a) if b["id"] != "t"]
    assert (new["type"], new["props"]["text"]) == ("text", "Der Hund ist braun und klein")


@pytest.mark.parametrize("target", ["list", "text", "cell", "sheet", "key"])
def test_the_next_account_pastes_no_words_of_the_one_before_into_any_target(editor, target):
    """#757: a copy's words stay on the clipboard; no field of the next account takes them."""
    a = user()
    page = editor(the_text_box(), client=a)
    copy_in_text(page)
    logout(page)
    b, email = someone()
    login(page, email, sheet(b, in_b_sheet()), 3)
    before = stored(page, b)
    if target == "list":
        field = open_list(page)
        field.press("Control+v")
        expect(field).to_have_value("")
    elif target == "text":
        pick(page, "t")
        page.keyboard.press("Enter")
        page.keyboard.press("End")
        page.keyboard.press("Control+v")
    elif target == "cell":
        pick(page, "c")
        at(page, "c").locator('.table > div[data-cell="0"]').dblclick()
        expect(at(page, "c").locator("textarea")).to_be_focused()
        page.keyboard.press("Control+v")
    elif target == "sheet":
        unpick(page)
        page.keyboard.press("Control+v")
    else:
        page.goto(f"{origin(page)}/konto")
        field = page.get_by_label("Name des Schlüssels")
        field.click()
        field.press("Control+v")
        expect(field).to_have_value("")
        page.go_back()
        ready(page, 3)
    if target != "key":
        expect(blocks(page)).to_have_count(3)
    assert stored(page, b) == before


def test_a_cut_in_an_open_text_pastes_nothing_for_the_next_account(editor):
    """#757: a cut is a copy too."""
    a, _ = someone()
    page = editor(the_text_box(), client=a)
    pick(page, "t")
    page.keyboard.press("Enter")
    page.keyboard.press("Home")
    page.keyboard.press("Shift+End")
    page.keyboard.press("Control+x")
    page.keyboard.press("Escape")
    page.keyboard.press("Escape")
    logout(page)
    next_list_paste_nothing(page)


def test_two_table_cells_copied_paste_nothing_for_the_next_account(editor):
    """#757: the cells' text, copied as a whole, is the editor's copy too."""
    a, _ = someone()
    page = editor(box("c", "table", CELLS), client=a)
    pick(page, "c")
    at(page, "c").locator('.table > div[data-cell="0"]').dblclick()
    expect(at(page, "c").locator("textarea")).to_be_focused()
    at(page, "c").locator('.table > div[data-cell="1"]').click(modifiers=["Shift"])
    expect(at(page, "c").locator(".table > div.picked")).to_have_count(2)
    page.keyboard.press("Control+c")
    assert page.evaluate("navigator.clipboard.readText()") == "Katze\tMaus"
    logout(page)
    next_list_paste_nothing(page)


def test_words_picked_in_the_list_field_paste_nothing_for_the_next_account(editor):
    """#757: a copy in the side panel's Lernwörter field is a copy in a field of the editor."""
    a, _ = someone()
    page = editor(box("x", "shape", RECT, w=40), client=a)
    field = open_list(page)
    field.fill("Hund\nKatze")
    field.press("Control+a")
    field.press("Control+c")
    logout(page)
    next_list_paste_nothing(page)


def test_a_text_with_a_gap_copied_whole_pastes_nothing_for_the_next_account(editor):
    """#757: the words of a Lückentext's copy are the copy's words, as the editor's own."""
    a, _ = someone()
    page = editor(box("t", "text", GAPPED), client=a)
    copy_in_text(page)
    logout(page)
    next_list_paste_nothing(page)


@chromium_only
def test_a_word_copied_then_again_in_another_app_pastes_as_a_text_block(editor):
    """#757: after the logout the copy's mark is gone: a word from another app is a text again."""
    a = user()
    page = editor(box("t", "text", {**TEXT, "text": "Hund"}), client=a)
    copy_in_text(page)
    logout(page)
    # Another app's copy, on the login page: no sheet to unpick.
    page.evaluate("(words) => navigator.clipboard.writeText(words)", "Hund")
    b, email = someone()
    login(page, email, sheet(b, [box("x", "shape", RECT, w=40)]), 1)
    page.keyboard.press("Control+v")
    expect(blocks(page)).to_have_count(2)
    [new] = [b for b in saved(page, b) if b["id"] != "x"]
    assert (new["type"], new["props"]["text"]) == ("text", "Hund")


@chromium_only
def test_words_copied_in_a_table_cell_paste_nothing_for_the_next_account(editor):
    """#757: a table cell's copy counts as the editor's: the next account's list gets none."""
    a = user()
    page = editor(box("c", "table", CELLS), client=a)
    pick(page, "c")
    at(page, "c").locator('.table > div[data-cell="0"]').dblclick()
    expect(at(page, "c").locator("textarea")).to_be_focused()
    page.keyboard.press("Control+a")
    page.keyboard.press("Control+c")
    page.keyboard.press("Escape")
    page.keyboard.press("Escape")
    assert page.evaluate("navigator.clipboard.readText()") == "Katze"
    logout(page)
    b, email = someone()
    login(page, email, sheet(b, [box("x", "shape", RECT, w=40)]), 1)
    before = stored(page, b)
    field = open_list(page)
    field.press("Control+v")
    expect(field).to_have_value("")
    assert stored(page, b) == before


def test_words_copied_on_the_login_page_paste_there_and_in_the_sheet(editor):
    """With no one signed in a copy is no account's: it pastes as any other words do."""
    a, email = someone()
    page = editor(the_text_box(), client=a)
    mine = {"id": page.url.rsplit("/", 1)[1]}
    logout(page)
    page.fill("#email", email)
    page.locator("#email").select_text()
    page.keyboard.press("Control+c")
    page.fill("#email", "")
    page.locator("#email").press("Control+v")
    expect(page.locator("#email")).to_have_value(email)
    login(page, email, mine, 1)
    unpick(page)
    page.keyboard.press("Control+v")
    expect(blocks(page)).to_have_count(2)


@chromium_only
def test_abmelden_empties_the_clipboard_of_a_key_copied_on_konto(editor):
    """#760: the key copied on Konto leaves the system clipboard at Abmelden."""
    a, _ = someone()
    page = editor(box("x", "shape", RECT, w=40), client=a)
    page.goto(f"{origin(page)}/konto")
    token = copy_key(page)
    assert page.evaluate("navigator.clipboard.readText()") == token
    logout(page)
    assert page.evaluate("navigator.clipboard.readText()") == ""


def test_the_next_account_pastes_no_key_copied_on_konto(editor):
    """#760: the next account pastes no key copied on Konto."""
    a, _ = someone()
    page = editor(box("x", "shape", RECT, w=40), client=a)
    page.goto(f"{origin(page)}/konto")
    copy_key(page)
    logout(page)
    next_list_paste_nothing(page)


def test_the_same_session_pastes_its_own_key_into_a_field(editor):
    """#760: the account that copied a key on Konto pastes it back there."""
    a, _ = someone()
    page = editor(box("x", "shape", RECT, w=40), client=a)
    page.goto(f"{origin(page)}/konto")
    token = copy_key(page)
    field = page.get_by_label("Name des Schlüssels")
    field.fill("")
    field.focus()
    # The copy's mark is set once the clipboard has taken the key: wait for it before the paste.
    assert page.evaluate("navigator.clipboard.readText()") == token
    page.keyboard.press("Control+v")
    expect(field).to_have_value(token)
