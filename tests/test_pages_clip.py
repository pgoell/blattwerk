"""Pages copied and cut from the panel Seiten, and pasted from its menu or from the keys."""

import re

from playwright.sync_api import expect
from test_clipboard import button
from test_clipboard_account import logout, origin, someone
from test_pages import OWN, three
from test_pages_many import expect_chosen, pick_many
from test_words import LINKED, go, rulings, store_words
from ui import BROWSER, PASSWORD, RECT, TEXT, box, doc, pick, sheet, thumb, user


def lettered(editor, **more):
    """Pages a, b and c, whose one text reads "A", "B" and "C": the copies show their order."""
    rest = [{"blocks": [box(name, "text", {**TEXT, "text": name.upper()})]} for name in "bc"]
    return editor(box("a", "text", {**TEXT, "text": "A"}), pages=rest, theme="", **more)


def words(page):
    """The text of the first block on each page, page by page."""
    count = page.locator(".sheet[data-page]").count()
    blocks = [page.locator(f'.sheet[data-page="{n}"] .block').first for n in range(count)]
    texts = [block.text_content() for block in blocks]
    return [text.strip() for text in texts]


def menu_item(page, name):
    # An item with keys shown after its name, as "KopierenStrg+C".
    return page.get_by_role("menuitem", name=re.compile(f"^{re.escape(name)}"))


def open_menu(page, n):
    thumb(page, n).click(button="right")
    expect(page.get_by_role("menuitem").first).to_be_visible()


def menu_run(page, n, name):
    open_menu(page, n)
    menu_item(page, name).click()
    expect(page.get_by_role("menuitem")).to_have_count(0)


def test_the_thumbnail_menu_offers_ausschneiden_kopieren_and_einfuegen(editor):
    """Ausschneiden, Kopieren and Einfügen come after the page items, in PowerPoint's order."""
    page = three(editor)
    open_menu(page, 1)
    expect(page.get_by_role("menuitem")).to_have_text(
        [
            "Neue Seite",
            "Seite duplizieren",
            "Seite löschen",
            re.compile(r"^Ausschneiden"),
            re.compile(r"^Kopieren"),
            re.compile(r"^Einfügen"),
        ]
    )
    page.keyboard.press("Escape")


def test_einfuegen_is_disabled_with_nothing_copied(editor):
    """Nothing copied yet: Einfügen is disabled."""
    page = three(editor)
    open_menu(page, 0)
    expect(menu_item(page, "Einfügen")).to_be_disabled()
    page.keyboard.press("Escape")


def test_kopieren_then_einfuegen_puts_the_copies_after_the_page(editor):
    """Two pages copied, then pasted after page b: the copies come in order, chosen; one undo."""
    page = lettered(editor)
    pick_many(page, 0, 1)
    menu_run(page, 1, "Kopieren")
    menu_run(page, 1, "Einfügen")
    expect(page.locator(".sheet[data-page]")).to_have_count(5)
    assert words(page) == ["A", "B", "A", "B", "C"]
    expect(page.locator(".sheet.on")).to_have_attribute("data-page", "2")
    expect_chosen(page, 2, 3)
    page.keyboard.press("Control+z")
    assert words(page) == ["A", "B", "C"]


def test_ausschneiden_takes_the_chosen_pages_and_einfuegen_brings_them_back_in_order(editor):
    """Pages a and c are cut, then pasted after page b: they come back in their order."""
    page = lettered(editor)
    pick_many(page, 0, 2)
    menu_run(page, 2, "Ausschneiden")
    assert words(page) == ["B"]
    menu_run(page, 0, "Einfügen")
    assert words(page) == ["B", "A", "C"]


def test_ausschneiden_is_disabled_when_it_would_take_every_page(editor):
    """With every page chosen, Ausschneiden is disabled, as Seite löschen is."""
    page = lettered(editor)
    pick_many(page, 0, 1, 2)
    open_menu(page, 1)
    expect(menu_item(page, "Ausschneiden")).to_be_disabled()
    page.keyboard.press("Escape")


def test_ctrl_c_x_v_on_a_thumbnail_copy_cut_and_paste_pages(editor):
    """Ctrl+X cuts the focused page, Ctrl+C copies it, Ctrl+V pastes after the focused page."""
    page = lettered(editor)
    thumb(page, 0).click()
    page.keyboard.press("Control+c")
    thumb(page, 2).focus()
    page.keyboard.press("Control+v")
    expect(page.locator(".sheet[data-page]")).to_have_count(4)
    assert words(page) == ["A", "B", "C", "A"]
    thumb(page, 1).click()
    page.keyboard.press("Control+x")
    assert words(page) == ["A", "C", "A"]


def test_ctrl_x_then_ctrl_v_on_the_thumbnails_moves_the_page(editor):
    """After Ctrl+X the focus stays on a thumbnail, so Ctrl+V pastes after the one in focus."""
    page = lettered(editor)
    thumb(page, 2).click()
    page.keyboard.press("Control+x")
    expect(thumb(page, 1)).to_be_focused()
    thumb(page, 0).focus()
    page.keyboard.press("Control+v")
    expect(page.locator(".sheet[data-page]")).to_have_count(3)
    assert words(page) == ["A", "C", "B"]


def test_blocks_copied_after_a_page_paste_as_blocks_from_a_thumbnail(editor):
    """The newest copy wins, as in PowerPoint: blocks copied after a page land as blocks."""
    page = lettered(editor)
    thumb(page, 0).click()
    page.keyboard.press("Control+c")
    pick(page, "a")
    page.keyboard.press("Control+c")
    thumb(page, 2).click()
    page.keyboard.press("Control+v")
    expect(page.locator('.sheet[data-page="2"] .block')).to_have_count(2)
    expect(page.locator(".sheet[data-page]")).to_have_count(3)


def test_ctrl_v_on_a_thumbnail_adds_a_page_and_no_block_lands_on_the_page_in_use(editor):
    """Ctrl+V adds one page; the page in use keeps its own block."""
    page = lettered(editor)
    thumb(page, 0).click()
    page.keyboard.press("Control+c")
    thumb(page, 2).click()
    page.keyboard.press("Control+v")
    expect(page.locator(".sheet[data-page]")).to_have_count(4)
    assert words(page) == ["A", "B", "C", "A"]
    assert page.locator('.sheet[data-page="2"] .block').count() == 1


def test_a_page_pasted_twice_gives_two_pages_with_blocks_of_new_ids(editor):
    """Two pastes of one copy: the two pages hold blocks of different ids."""
    page = lettered(editor)
    menu_run(page, 0, "Kopieren")
    menu_run(page, 0, "Einfügen")
    menu_run(page, 0, "Einfügen")
    expect(page.locator(".sheet[data-page]")).to_have_count(5)
    first = page.locator('.sheet[data-page="1"] .block').first.get_attribute("data-id")
    second = page.locator('.sheet[data-page="2"] .block').first.get_attribute("data-id")
    assert first and second and first != second


def test_a_page_copied_in_one_tab_pastes_in_another(editor):
    """Copied in one tab, pasted from the menu of a sheet open in a second tab."""
    page = lettered(editor)
    menu_run(page, 1, "Kopieren")
    other = page.context.new_page()
    other.goto(page.url)
    expect(other.locator('main.editor[data-ready="1"]')).to_be_visible(timeout=10000)
    expect(thumb(other, 2)).to_be_visible()
    menu_run(other, 2, "Einfügen")
    expect(other.locator(".sheet[data-page]")).to_have_count(4)
    assert words(other) == ["A", "B", "C", "B"]
    other.close()


def test_another_account_pastes_no_pages(editor):
    """After a logout and a login as another account, Einfügen pastes nothing."""
    page = lettered(editor)
    menu_run(page, 1, "Kopieren")
    logout(page)
    assert page.evaluate("localStorage.getItem('pages')") is None
    b, email = someone()
    # The login form as a teacher uses it. The other account's sheet opens with its panel shut.
    page.fill("#email", email)
    page.fill("#password", PASSWORD)
    with page.expect_response("**/api/login") as answer:
        button(page, "Anmelden").click()
    assert answer.value.ok
    if BROWSER == "webkit":
        # As in tests/test_clipboard_account.py: WebKit drops the Secure cookie of this http server,
        # so the page's next calls get 401 and the form comes back after some ms (#727).
        # The cookie goes by hand.
        value = answer.value.header_value("set-cookie").split(";")[0].split("=", 1)[1]
        page.context.add_cookies([{"name": "session", "value": value, "url": origin(page)}])
    else:
        expect(page.locator("#email")).to_have_count(0)
    page.goto(f"{origin(page)}/blatt/{sheet(b, [box('x', 'shape', RECT, w=40)])['id']}")
    expect(page.locator('main.editor[data-ready="1"]')).to_be_visible(timeout=10000)
    expect(page.locator(".sheet[data-page]")).to_have_count(1)
    assert page.evaluate("localStorage.getItem('pages')") is None


def test_a_pasted_page_keeps_its_guide_lines_grid_and_format(editor):
    """Einfügen brings the page's own guide lines, grid and format, as Seite duplizieren does."""
    client = user()
    rest = [{"blocks": [box("b", "text", TEXT)], **OWN}]
    page = editor(box("a", "text", TEXT), client=client, pages=rest, theme="")
    thumb(page, 1).click()
    page.keyboard.press("Control+c")
    thumb(page, 0).focus()
    page.keyboard.press("Control+v")
    expect(page.locator(".sheet[data-page]")).to_have_count(3)
    first, second, third = doc(page, client)["pages"]
    assert {key: second[key] for key in OWN} == OWN
    assert {key: third[key] for key in OWN} == OWN
    assert not OWN.keys() & first.keys()


def test_a_pasted_page_with_a_linked_lineatur_takes_the_list_to_a_sheet_without_one(editor):
    """The page's linked Lineatur brings the word list along, as a copied linked block does."""
    client = user()
    page = editor(box("r", "ruling", LINKED), client=client, theme="")
    store_words(page, client, ["Hund", "Katze"])
    other = sheet(client, [box("t", "text", TEXT, z=3)])
    thumb(page, 0).click()
    page.keyboard.press("Control+c")
    go(page, other)
    thumb(page, 0).click()
    page.keyboard.press("Control+v")
    expect(page.locator(".sheet[data-page]")).to_have_count(2)
    stored = doc(page, client)
    assert stored["words"] == ["Hund", "Katze"]
    assert rulings(stored, 1)[0]["props"]["list"] == "copy"
