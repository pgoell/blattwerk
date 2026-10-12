"""The Lernwörter: a sheet's list, the Lineatur that takes it, the Blatt, and copies of both."""

import pytest
from playwright.sync_api import expect
from test_keys_focus import choose
from ui import RULING, TEXT, at, box, copy_text, doc, pick, sheet, thumb, unpick, user

LINKED = {**RULING, "list": "copy"}
MODES = ["copy", "trace", "row"]


@pytest.fixture
def editor(editor):
    """The editor with its panel open, where the tabs Format and Lernwörter are."""

    def start(*blocks, **more):
        return editor(*blocks, theme="", **more)

    return start


def ready(page):
    expect(page.locator('main.editor[data-ready="1"]')).to_be_visible()


def list_tab(page):
    page.get_by_role("tab", name="Lernwörter").click()


def field(page):
    return page.get_by_label("Lernwörter", exact=True)


def undo(page):
    page.get_by_label("Rückgängig", exact=True).first.click()


def redo(page):
    page.get_by_label("Wiederholen", exact=True).click()


def store_words(page, client, words):
    """Stores the sheet's list as the server holds it, then opens the sheet again."""
    sheet_id = page.url.rsplit("/", 1)[1]
    got = client.get(f"/api/sheets/{sheet_id}").json()
    body = {"doc": {**got["doc"], "words": words}, "version": got["version"]}
    assert client.patch(f"/api/sheets/{sheet_id}", json=body).status_code == 200
    page.reload()
    ready(page)


def go(page, other):
    """Opens another sheet of the same user in this tab."""
    page.goto(f"{page.url.rsplit('/blatt/', 1)[0]}/blatt/{other['id']}")
    ready(page)
    page.bring_to_front()


def rulings(stored, n=0):
    return [b for b in stored["pages"][n]["blocks"] if b["type"] == "ruling"]


def state(stored):
    """The sheet's list, and what the first Lineatur holds of it: its mode and its own text."""
    props = rulings(stored)[0]["props"]
    return stored.get("words"), props.get("list"), props.get("text"), props.get("trace")


def test_the_list_typed_in_the_tab_is_stored_with_the_sheet(editor):
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    list_tab(page)
    field(page).click()
    page.keyboard.type("Hund")
    page.keyboard.press("Enter")
    page.keyboard.type("Katze")
    assert doc(page, client)["words"] == ["Hund", "Katze"]
    page.reload()
    ready(page)
    list_tab(page)
    expect(field(page)).to_have_value("Hund\nKatze")


def test_a_pasted_list_lands_one_word_to_a_line(editor):
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    list_tab(page)
    field(page).click()
    page.keyboard.type("Igel")
    page.keyboard.press("Enter")
    copy_text(page, "Hund, Katze;Maus\r\nReh")
    field(page).focus()
    page.keyboard.press("Control+End")
    page.keyboard.press("Control+v")
    expect(field(page)).to_have_value("Igel\nHund\nKatze\nMaus\nReh")
    assert doc(page, client)["words"] == ["Igel", "Hund", "Katze", "Maus", "Reh"]


@pytest.mark.parametrize("mode", MODES)
def test_the_choice_links_a_lineatur(editor, mode):
    client = user()
    page = editor(box("r", "ruling", RULING), client=client)
    store_words(page, client, ["Hund", "Katze"])
    pick(page, "r")
    page.get_by_label("Text der Lineatur").select_option(mode)
    expect(page.get_by_label("Text der Lineatur")).to_have_value(mode)
    assert rulings(doc(page, client))[0]["props"]["list"] == mode
    expect(page.get_by_role("button", name="Nachspurtext")).to_have_count(0)
    expect(page.get_by_text("Doppelklick auf die Lineatur")).to_have_count(0)
    expect(page.get_by_label("Schriftart auf den Zeilen")).to_be_visible()


def test_a_linked_block_grows_to_hold_every_word(editor):
    client = user()
    page = editor(box("r", "ruling", RULING, h=20), client=client)
    store_words(page, client, ["Hund", "Katze", "Maus", "Reh", "Igel"])
    pick(page, "r")
    page.get_by_label("Text der Lineatur").select_option("copy")
    grown = rulings(doc(page, client))[0]
    assert grown["h"] == 50
    assert grown["props"]["list"] == "copy"
    undo(page)
    back = rulings(doc(page, client))[0]
    assert back["h"] == 20
    assert "list" not in back["props"]


@pytest.mark.parametrize("case", ["margin", "locked"])
def test_a_block_that_cannot_grow_says_how_many_words_do_not_fit(editor, case):
    client = user()
    if case == "margin":
        # The bottom margin lies at 282 mm: the ruling has room for two rows only.
        page = editor(box("r", "ruling", RULING, y=262), client=client)
        words = ["Hund", "Katze", "Maus", "Reh", "Igel"]
        warning = "3 Wörter passen nicht in die Zeilen."
    else:
        page = editor(box("r", "ruling", RULING, locked=True), client=client)
        words, warning = ["Hund", "Katze", "Maus"], "1 Wort passt nicht in die Zeilen."
    store_words(page, client, words)
    pick(page, "r")
    page.get_by_label("Text der Lineatur").select_option("copy")
    expect(page.locator(".panel [role=status]")).to_have_text(warning)
    assert rulings(doc(page, client))[0]["h"] == 20


def test_a_list_that_grows_later_warns_and_moves_no_block(editor):
    client = user()
    page = editor(box("r", "ruling", LINKED, h=20), client=client)
    store_words(page, client, ["Hund", "Katze"])
    list_tab(page)
    field(page).focus()
    page.keyboard.press("Control+End")
    page.keyboard.press("Enter")
    page.keyboard.type("Maus")
    expect(field(page)).to_have_value("Hund\nKatze\nMaus")
    assert rulings(doc(page, client))[0]["h"] == 20
    page.get_by_role("tab", name="Format").click()
    pick(page, "r")
    expect(page.locator(".panel [role=status]")).to_have_text("1 Wort passt nicht in die Zeilen.")


@pytest.mark.parametrize("mode", MODES)
def test_cut_loose_keeps_the_words_as_plain_text(editor, mode):
    client = user()
    page = editor(box("r", "ruling", {**RULING, "list": mode}), client=client)
    store_words(page, client, ["Hund", "Katze"])
    pick(page, "r")
    page.get_by_label("Text der Lineatur").select_option("own")
    props = rulings(doc(page, client))[0]["props"]
    assert "list" not in props
    assert props["text"] == "Hund\nKatze"
    # Trace and row keep their grey text over the words, as they did on the list; copy has none.
    if mode == "copy":
        assert "trace" not in props
    else:
        assert props["trace"] is True
    expect(at(page, "r").locator("textarea.written")).to_have_value("Hund\nKatze")


def test_the_lernwoerter_blatt_is_a_new_page_in_one_step(editor):
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    store_words(page, client, ["Hund", "Katze", "Igel"])
    list_tab(page)
    page.get_by_role("button", name="Lernwörter-Blatt").click()
    stored = doc(page, client)
    assert len(stored["pages"]) == 2
    blatt = stored["pages"][1]["blocks"]
    assert [b["type"] for b in blatt] == ["text", "name", "ruling", "ruling", "ruling"]
    assert blatt[0]["props"]["text"] == "Lernwörter"
    lines = blatt[2:]
    assert [b["props"]["list"] for b in lines] == ["copy", "trace", "row"]
    assert [b["y"] for b in lines] == sorted(b["y"] for b in lines)
    assert all(b["props"]["kind"] == "l2" and b["h"] == 48 for b in lines)
    undo(page)
    assert len(doc(page, client)["pages"]) == 1
    redo(page)
    assert len(doc(page, client)["pages"]) == 2


def test_the_blatt_button_is_off_without_words(editor):
    page = editor(box("a", "text", TEXT), client=user())
    list_tab(page)
    expect(page.get_by_role("button", name="Lernwörter-Blatt")).to_be_disabled()


def test_the_blatt_takes_the_lineatur_that_holds_every_word(editor):
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    store_words(page, client, ["Hund", "Katze", "Maus", "Reh", "Igel", "Fuchs"])
    list_tab(page)
    page.get_by_role("button", name="Lernwörter-Blatt").click()
    lines = doc(page, client)["pages"][1]["blocks"][2:]
    # Six words need six rows: Lineatur 3 fits them in a third of the page, Lineatur 2 does not.
    assert all(b["props"]["kind"] == "l3" for b in lines)


def test_undo_and_redo_walk_the_list_the_link_the_mode_and_the_cut(editor):
    client = user()
    page = editor(box("r", "ruling", RULING), client=client)
    list_tab(page)
    field(page).click()
    page.keyboard.type("Hund")
    expect(field(page)).to_have_value("Hund")
    pick(page, "r")
    page.get_by_role("tab", name="Format").click()
    select = page.get_by_label("Text der Lineatur")
    select.select_option("copy")
    select.select_option("row")
    select.select_option("own")
    expect(select).to_have_value("own")
    steps = [
        (None, None, None, None),
        (["Hund"], None, None, None),
        (["Hund"], "copy", None, None),
        (["Hund"], "row", None, None),
        (["Hund"], None, "Hund", True),
    ]
    assert state(doc(page, client)) == steps[4]
    for want in [steps[3], steps[2], steps[1], steps[0]]:
        undo(page)
        assert state(doc(page, client)) == want
    for want in steps[1:]:
        redo(page)
        assert state(doc(page, client)) == want


def test_a_run_of_typing_in_the_list_is_one_undo_step(editor):
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    list_tab(page)
    field(page).click()
    page.keyboard.type("Hund")
    page.keyboard.press("Enter")
    page.keyboard.type("Katze")
    expect(field(page)).to_have_value("Hund\nKatze")
    undo(page)
    assert "words" not in doc(page, client)
    expect(field(page)).to_have_value("")


def test_ctrl_z_in_the_list_undoes_the_sheet(editor):
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    list_tab(page)
    field(page).click()
    page.keyboard.type("Hund")
    expect(field(page)).to_have_value("Hund")
    page.keyboard.press("Control+z")
    expect(field(page)).to_have_value("")
    assert "words" not in doc(page, client)


def test_several_lineaturen_link_in_one_step(editor):
    client = user()
    page = editor(
        box("a", "ruling", {**RULING, "list": "trace"}),
        box("b", "ruling", RULING, z=2),
        client=client,
    )
    store_words(page, client, ["Hund", "Katze"])
    pick(page, "a", "b")
    select = page.get_by_label("Text der Lineatur")
    expect(select).to_have_value("own")
    select.select_option("copy")
    assert [r["props"]["list"] for r in rulings(doc(page, client))] == ["copy", "copy"]
    undo(page)
    assert [r["props"].get("list") for r in rulings(doc(page, client))] == ["trace", None]
    select.select_option("row")
    unpick(page)
    pick(page, "a", "b")
    expect(page.get_by_label("Text der Lineatur")).to_have_value("row")


@pytest.mark.parametrize("how", ["dblclick", "enter", "typing"])
def test_a_linked_block_opens_no_field(editor, how):
    client = user()
    page = editor(box("r", "ruling", {**LINKED, "text": "eigen"}), client=client)
    store_words(page, client, ["Hund", "Katze"])
    if how == "dblclick":
        at(page, "r").dblclick()
    else:
        pick(page, "r")
        if how == "enter":
            page.keyboard.press("Enter")
        else:
            page.keyboard.type("x")
    expect(page.locator("textarea.written:not([readonly])")).to_have_count(0)
    stored = doc(page, client)
    assert rulings(stored)[0]["props"]["text"] == "eigen"
    assert stored["words"] == ["Hund", "Katze"]


def test_a_sheet_without_a_list_saves_back_as_it_was(editor):
    client = user()
    page = editor(box("r", "ruling", RULING), client=client)
    pick(page, "r")
    page.keyboard.press("ArrowRight")
    stored = doc(page, client)
    assert rulings(stored)[0]["x"] == 16
    assert "words" not in stored
    assert "list" not in rulings(stored)[0]["props"]


def test_emptying_the_list_removes_it(editor):
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    store_words(page, client, ["Hund"])
    list_tab(page)
    field(page).fill("")
    assert "words" not in doc(page, client)


@pytest.mark.parametrize("junk", ["Hund", 7])
def test_garbage_in_words_shows_an_empty_list(editor, junk):
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    store_words(page, client, junk)
    list_tab(page)
    expect(field(page)).to_have_value("")
    expect(page.get_by_role("button", name="Lernwörter-Blatt")).to_be_disabled()
    field(page).click()
    page.keyboard.type("Reh")
    assert doc(page, client)["words"] == ["Reh"]


def test_a_reload_a_duplicate_and_a_template_keep_the_list(editor):
    client = user()
    page = editor(box("r", "ruling", LINKED), client=client)
    store_words(page, client, ["Hund", "Katze"])
    page.reload()
    ready(page)
    stored = doc(page, client)
    assert stored["words"] == ["Hund", "Katze"]
    assert rulings(stored)[0]["props"]["list"] == "copy"

    sheet_id = page.url.rsplit("/", 1)[1]
    copied = client.post(f"/api/sheets/{sheet_id}/duplicate").json()["doc"]
    assert copied["words"] == ["Hund", "Katze"]
    assert rulings(copied)[0]["props"]["list"] == "copy"

    page.get_by_label("Name der Vorlage").fill("Lernwörter-Vorlage")
    page.get_by_role("button", name="Dieses Blatt als Vorlage").click()
    other = sheet(client, [])
    go(page, other)
    page.get_by_role("button", name="Lernwörter-Vorlage", exact=True).click()
    stored = doc(page, client)
    assert stored["words"] == ["Hund", "Katze"]
    assert rulings(stored)[0]["props"]["list"] == "copy"


def test_a_copied_linked_block_takes_the_list_to_a_sheet_without_one(editor):
    client = user()
    page = editor(box("r", "ruling", LINKED), client=client)
    store_words(page, client, ["Hund", "Katze"])
    other = sheet(client, [box("t", "text", TEXT, z=3)])
    pick(page, "r")
    page.keyboard.press("Control+c")
    go(page, other)
    page.keyboard.press("Control+v")
    expect(page.locator(".sheet .block")).to_have_count(2)
    stored = doc(page, client)
    assert stored["words"] == ["Hund", "Katze"]
    assert rulings(stored)[0]["props"]["list"] == "copy"
    undo(page)
    stored = doc(page, client)
    assert "words" not in stored
    assert rulings(stored) == []


def test_a_copied_linked_block_lands_cut_loose_on_a_sheet_with_another_list(editor):
    client = user()
    page = editor(box("r", "ruling", LINKED), client=client)
    store_words(page, client, ["Hund", "Katze"])
    other = sheet(client, [box("t", "text", TEXT, z=3)])
    pick(page, "r")
    page.keyboard.press("Control+c")
    go(page, other)
    store_words(page, client, ["Reh"])
    page.keyboard.press("Control+v")
    expect(page.locator(".sheet .block")).to_have_count(2)
    stored = doc(page, client)
    assert stored["words"] == ["Reh"]
    props = rulings(stored)[0]["props"]
    # Another list than the sheet's: the words go in as the block's own text.
    assert "list" not in props
    assert props["text"] == "Hund\nKatze"


def test_a_duplicated_block_and_a_copied_page_stay_linked(editor):
    client = user()
    page = editor(box("r", "ruling", LINKED), client=client)
    store_words(page, client, ["Hund", "Katze"])
    pick(page, "r")
    page.keyboard.press("Control+d")
    expect(page.locator(".sheet .block")).to_have_count(2)
    thumb(page, 0).focus()
    page.keyboard.press("Control+d")
    stored = doc(page, client)
    assert stored["words"] == ["Hund", "Katze"]
    assert len(stored["pages"]) == 2
    assert [r["props"].get("list") for r in rulings(stored)] == ["copy", "copy"]
    assert [r["props"].get("list") for r in rulings(stored, 1)] == ["copy", "copy"]


def test_tab_reaches_the_list_controls_and_keys_press_them(editor):
    client = user()
    page = editor(box("r", "ruling", RULING), client=client)
    pick(page, "r")
    page.get_by_label("Art der Lineatur").focus()
    for _ in range(12):
        if page.get_by_label("Text der Lineatur").evaluate("el => el === document.activeElement"):
            break
        page.keyboard.press("Tab")
    expect(page.get_by_label("Text der Lineatur")).to_be_focused()
    page.keyboard.press("ArrowDown")
    expect(page.get_by_label("Text der Lineatur")).to_have_value("copy")
    assert rulings(doc(page, client))[0]["props"]["list"] == "copy"

    store_words(page, client, ["Hund"])
    list_tab(page)
    field(page).focus()
    page.keyboard.press("Tab")
    expect(page.get_by_role("button", name="Lernwörter-Blatt")).to_be_focused()
    page.keyboard.press("Enter")
    assert len(doc(page, client)["pages"]) == 2


def test_a_change_to_the_list_reaches_every_linked_block_in_one_undo_step(editor):
    """A6: the blocks draw from the list, on the page in use and on the others."""
    client = user()
    page = editor(
        box("a", "ruling", {**RULING, "list": "copy"}, h=40),
        box("o", "ruling", {**RULING, "list": "row"}, y=120, h=40, z=2),
        more=[box("b", "ruling", {**RULING, "list": "trace"}, h=40)],
        client=client,
        words=["Hund"],
    )
    for block in (at(page, "a"), at(page, "o"), thumb(page, 1).locator(".block")):
        expect(block.locator(".listed .row")).to_have_count(1)
    list_tab(page)
    field(page).press("Control+End")
    field(page).press_sequentially("\nKatze\nMaus")
    for block in (at(page, "a"), at(page, "o"), thumb(page, 1).locator(".block")):
        expect(block.locator(".listed .row")).to_have_count(3)
        expect(block.locator(".listed .row").nth(2).locator("span").first).to_have_text("Maus")
    assert doc(page, client)["words"] == ["Hund", "Katze", "Maus"]
    undo(page)
    for block in (at(page, "a"), at(page, "o"), thumb(page, 1).locator(".block")):
        expect(block.locator(".listed .row")).to_have_count(1)
    assert doc(page, client)["words"] == ["Hund"]
    redo(page)
    expect(at(page, "a").locator(".listed .row")).to_have_count(3)


def test_the_choice_gives_the_keys_back_to_the_sheet_and_ends_the_writing(editor):
    """A pick in the list with the mouse leaves the keys with the sheet, as the panel's other
    lists do, and a Lineatur being written in is no longer: linked, it has no field."""
    client = user()
    page = editor(box("a", "ruling", {**RULING, "text": "eigen"}, h=40), client=client)
    store_words(page, client, ["Hund"])
    pick(page, "a")
    page.keyboard.press("Enter")
    expect(at(page, "a").locator("textarea.written:not([readonly])")).to_be_focused()
    control = choose(page, "Text der Lineatur")
    expect(control).not_to_be_focused()
    expect(at(page, "a").locator("textarea")).to_have_count(0)
    expect(at(page, "a").locator(".listed .row span")).to_have_text("Hund")
    page.keyboard.press("ArrowRight")
    expect(page.get_by_label("X", exact=True)).to_have_value("16")
    # Cut loose again, the block is not being written in.
    page.locator(".panel").get_by_label("Text der Lineatur").select_option("own")
    expect(at(page, "a").locator("textarea.written")).to_have_attribute("readonly", "")
    assert rulings(doc(page, client))[0]["props"]["text"] == "Hund"


def test_a_list_too_long_for_the_blatt_is_said_on_the_tab(editor):
    """Review: the Lernwörter-Blatt picks no block, so the tab itself says what does not fit."""
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    store_words(page, client, [f"Wort{n}" for n in range(12)])
    list_tab(page)
    expect(page.locator(".panel [role=status]")).to_have_count(0)
    page.get_by_role("button", name="Lernwörter-Blatt").click()
    said = "In einer Lineatur passen 3 Wörter nicht in die Zeilen."
    expect(page.locator(".panel [role=status]")).to_have_text(said)
    assert [b["h"] for b in rulings(doc(page, client), 1)] == [72, 72, 72]


def test_a_lineatur_in_a_group_with_a_locked_block_takes_the_list_and_does_not_grow(editor):
    """Review: such a block is as fixed as the locked one, as "Bis Seitenende" has it."""
    client = user()
    page = editor(
        box("r", "ruling", RULING, group=["g"]),
        box("t", "text", TEXT, y=150, z=2, locked=True, group=["g"]),
        client=client,
    )
    store_words(page, client, ["Hund", "Katze", "Maus", "Reh", "Igel"])
    at(page, "r").click()
    page.get_by_label("Text der Lineatur").select_option("copy")
    stored = rulings(doc(page, client))[0]
    assert (stored["props"]["list"], stored["h"]) == ("copy", 20)
    said = "3 Wörter passen nicht in die Zeilen."
    expect(page.locator(".panel [role=status]")).to_have_text(said)


def test_a_paste_beside_a_word_joins_no_word_to_it(editor):
    """Review: pasted words keep to lines of their own, behind a word and before one."""
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    list_tab(page)
    field(page).click()
    page.keyboard.type("Igel")
    copy_text(page, "Hund, Katze")
    field(page).focus()
    page.keyboard.press("Control+End")
    page.keyboard.press("Control+v")
    expect(field(page)).to_have_value("Igel\nHund\nKatze")
    page.keyboard.press("Control+Home")
    page.keyboard.press("Control+v")
    expect(field(page)).to_have_value("Hund\nKatze\nIgel\nHund\nKatze")
    assert doc(page, client)["words"] == ["Hund", "Katze", "Igel", "Hund", "Katze"]
