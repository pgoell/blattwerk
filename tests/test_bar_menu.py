"""Mehr: the commands that fold into it, and running them from there.

The bar helpers live in test_bar.py."""

from conftest import IPAD, TURNED
from playwright.sync_api import expect
from test_bar import (
    BAR,
    LAST,
    ZOOM,
    expect_fitted,
    item,
    menu,
    more,
    resize,
    sized,
    text,
)
from ui import (
    TEXT,
    apart,
    at,
    box,
    expect_picked,
    maths,
    pick,
    saved,
    tool,
    user,
)


def test_a_command_in_mehr_is_off_where_its_button_is_off(editor):
    """A3"""
    page = sized(editor, text("a"), text("b", 2), width=701, height=1000, touch=False, theme="")
    expect_fitted(page)
    needs = ["Format übertragen", "Duplizieren", "Löschen", "Sperren"]
    more(page).click()
    for name in (*needs, "Gruppieren", "Gruppierung aufheben"):
        expect(item(page, name)).to_be_disabled()
    for name in ("Lösungen zeigen", *ZOOM, *LAST):
        expect(item(page, name)).to_be_enabled()
    page.keyboard.press("Escape")
    pick(page, "a")
    more(page).click()
    for name in needs:
        expect(item(page, name)).to_be_enabled()
    expect(item(page, "Gruppieren")).to_be_disabled()
    page.keyboard.press("Escape")
    pick(page, "a", "b")
    more(page).click()
    expect(item(page, "Gruppieren")).to_be_enabled()
    expect(item(page, "Gruppierung aufheben")).to_be_disabled()


def test_commands_run_from_mehr_do_what_their_buttons_do(editor):
    """A3"""
    client = user()
    blocks = [text("a"), box("m", "maths", maths(client), z=2)]
    page = sized(editor, *blocks, client=client, width=768, height=1024, touch=True, theme="")
    expect_fitted(page)
    assert "Kopieren" not in page.evaluate(BAR)["names"]
    at(page, "a").tap()
    expect_picked(page, "a")
    tool(page, "Kopieren").tap()
    expect(menu(page)).to_have_count(0)
    tool(page, "Einfügen").tap()
    expect(page.locator(".block[data-id]")).to_have_count(3)
    tool(page, "Löschen").tap()
    expect(page.locator(".block[data-id]")).to_have_count(2)
    # The answers show in the sums.
    answer = at(page, "m").locator("u").first
    expect(answer).to_have_text("")
    tool(page, "Lösungen zeigen").tap()
    expect(answer).not_to_have_text("")
    width = page.locator(".sheet").first.bounding_box()["width"]
    tool(page, "Größer").tap()
    page.wait_for_function(
        "(was) => document.querySelector('.sheet').getBoundingClientRect().width > was * 1.2",
        arg=width,
    )
    tool(page, "Rundgang").tap()
    expect(page.locator(".tour h2")).to_have_text("Willkommen bei Blattomat")
    page.locator(".tour").get_by_text("Beenden").tap()
    tool(page, "Feedback").tap()
    form = page.locator("dialog.feedback")
    expect(form).to_be_visible()
    # What is written in the form stays when the bar is fitted anew under it.
    form.get_by_label("Schreiben").fill("zu eng")
    resize(page, **TURNED)
    expect_fitted(page)
    expect(form).to_be_visible()
    expect(form.get_by_label("Schreiben")).to_have_value("zu eng")
    resize(page, **IPAD)
    expect_fitted(page)
    expect(form.get_by_label("Schreiben")).to_have_value("zu eng")


def test_format_uebertragen_from_mehr_stays_on_until_it_is_picked_again(editor):
    """A3: a menu has no double click, so the brush picked there paints block after block."""
    client = user()
    blocks = apart(
        box("a", "text", {**TEXT, "bold": True}), text("b", 2), text("c", 3), text("d", 4)
    )
    page = editor(*blocks, client=client, touch=True, theme="")
    expect_fitted(page)
    assert "Format übertragen" not in page.evaluate(BAR)["names"]
    at(page, "a").tap()
    expect_picked(page, "a")
    tool(page, "Format übertragen").tap()
    brushing = page.locator("main.editor.brush")
    expect(brushing).to_have_count(1)
    for name in "bc":
        at(page, name).tap()
        expect_picked(page, name)
        expect(brushing).to_have_count(1)
    # The item shows that the brush is on, and picking it again puts the brush down.
    more(page).tap()
    expect(item(page, "Format übertragen")).to_have_attribute("aria-checked", "true")
    item(page, "Format übertragen").tap()
    expect(brushing).to_have_count(0)
    at(page, "d").tap()
    expect_picked(page, "d")
    more(page).tap()
    expect(item(page, "Format übertragen")).to_have_attribute("aria-checked", "false")
    page.keyboard.press("Escape")
    look = {b["id"]: b["props"].get("bold", False) for b in saved(page, client)}
    assert look == {"a": True, "b": True, "c": True, "d": False}


def test_mehr_opens_by_a_tap(editor):
    """A4"""
    page = editor(text("a"), touch=True)
    expect_fitted(page)
    more(page).tap()
    expect(menu(page)).to_be_visible()
    expect(more(page)).to_have_attribute("aria-expanded", "true")
    # The menu lies in the window, under its button.
    place, under = menu(page).bounding_box(), more(page).bounding_box()
    assert place["y"] >= under["y"] + under["height"]
    assert place["x"] >= 0 and place["x"] + place["width"] <= IPAD["width"]
    assert place["y"] + place["height"] <= IPAD["height"]
    # A tap beside it shuts it.
    page.touchscreen.tap(100, 900)
    expect(menu(page)).to_have_count(0)


def test_mehr_opens_and_runs_by_the_keys(editor):
    """A4"""
    page = sized(editor, text("a"), width=900, height=1200, touch=False, theme="")
    expect_fitted(page)
    page.get_by_label("Titel").focus()
    for _ in range(30):
        if more(page).evaluate("el => el === document.activeElement"):
            break
        page.keyboard.press("Tab")
    expect(more(page)).to_be_focused()
    for key in ("Enter", "Space"):
        page.keyboard.press(key)
        expect(menu(page)).to_be_visible()
        items = menu(page).locator("button")
        # The first command that is on has the focus, and the arrows walk from it.
        expect(items.nth(0)).to_be_focused()
        page.keyboard.press("ArrowDown")
        expect(items.nth(1)).to_be_focused()
        page.keyboard.press("ArrowUp")
        expect(items.nth(0)).to_be_focused()
        page.keyboard.press("Escape")
        expect(menu(page)).to_have_count(0)
        expect(more(page)).to_be_focused()
    # Enter runs the command the focus is on.
    page.keyboard.press("Enter")
    expect(item(page, "Lösungen zeigen")).to_be_focused()
    page.keyboard.press("Enter")
    expect(menu(page)).to_have_count(0)
    expect(more(page)).to_be_focused()
    page.keyboard.press("Enter")
    expect(item(page, "Lösungen zeigen")).to_have_attribute("aria-checked", "true")


def test_a_command_from_mehr_acts_on_the_whole_selection_as_one_step_of_undo(editor):
    """I1"""
    page = sized(editor, text("a"), text("b", 2), width=768, height=1024, touch=False, theme="")
    expect_fitted(page)
    undo = page.get_by_label("Rückgängig", exact=True)
    pick(page, "a", "b")
    tool(page, "Löschen").click()
    expect(page.locator(".block[data-id]")).to_have_count(0)
    undo.click()
    expect(page.locator(".block[data-id]")).to_have_count(2)
    expect(undo).to_be_disabled()


def test_mehr_shows_what_is_on(editor):
    """I2"""
    blocks = [text("a"), text("b", 2, locked=True)]
    page = sized(editor, *blocks, width=768, height=1024, touch=False, theme="")
    expect_fitted(page)
    more(page).click()
    expect(item(page, "Lösungen zeigen")).to_have_attribute("aria-checked", "false")
    item(page, "Lösungen zeigen").click()
    more(page).click()
    expect(item(page, "Lösungen zeigen")).to_have_attribute("aria-checked", "true")
    # A tick stands at the end of its row.
    tick = "el => getComputedStyle(el, '::after').content"
    assert item(page, "Lösungen zeigen").evaluate(tick) == '"✓"'
    assert item(page, "Kleiner").evaluate(tick) == "none"
    expect(item(page, "Sperren")).to_be_visible()
    page.keyboard.press("Escape")
    pick(page, "b")
    more(page).click()
    expect(item(page, "Entsperren")).to_be_enabled()
    expect(item(page, "Sperren")).to_have_count(0)
    item(page, "Entsperren").click()
    more(page).click()
    expect(item(page, "Sperren")).to_be_enabled()
