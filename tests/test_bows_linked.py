"""Silbenbögen and Silbenfarbe on a Lineatur that is linked to the Lernwörter (#719)."""

import pytest
from playwright.sync_api import expect
from test_words import list_tab, rulings, undo
from ui import RULING, at, box, doc, pick, sheet, user

from blattwerk import pdf

WORDS = ["Hase", "Igel", "Kaninchen"]
MODES = ["copy", "trace", "row", "fold"]


@pytest.fixture
def editor(editor):
    """The editor with its panel open, where the tabs Format and Lernwörter are."""

    def start(*blocks, **more):
        return editor(*blocks, theme="", **more)

    return start


def test_a_linked_lineatur_has_the_syllable_buttons_and_they_draw_bows(editor):
    client = user()
    page = editor(client=client, words=WORDS)
    list_tab(page)
    page.get_by_role("button", name="Lernwörter-Blatt").click()
    first = rulings(doc(page, client))[0]["id"]
    pick(page, first)
    bows = page.get_by_role("button", name="Silbenbögen")
    expect(bows).to_be_visible()
    bows.click()
    expect(at(page, first).locator(".syl").first).to_be_visible()
    bows.click()
    expect(at(page, first).locator(".syl")).to_have_count(0)
    undo(page)
    expect(at(page, first).locator(".syl").first).to_be_visible()


@pytest.mark.parametrize("mode", MODES)
def test_a_list_mode_lineatur_has_the_colour_button_and_it_sets_the_colours(editor, mode):
    client = user()
    page = editor(box("lined", "ruling", {**RULING, "list": mode}), client=client, words=WORDS)
    pick(page, "lined")
    colours = page.get_by_role("button", name="Silbenfarbe")
    expect(colours).to_be_visible()
    colours.click()
    expect(colours).to_have_attribute("aria-pressed", "true")
    assert rulings(doc(page, client))[0]["props"]["tints"] is not None


def test_a_linked_and_an_own_text_lineatur_picked_together_take_the_bows_in_one_press(editor):
    client = user()
    page = editor(
        box("lined", "ruling", {**RULING, "list": "copy"}),
        box("own", "ruling", {**RULING, "text": "Sonne"}, z=2),
        client=client,
        words=WORDS,
    )
    pick(page, "lined", "own")
    page.get_by_role("button", name="Silbenbögen").click()
    expect(at(page, "lined").locator(".syl").first).to_be_visible()
    expect(at(page, "own").locator(".syl").first).to_be_visible()
    stored = rulings(doc(page, client))
    assert [r["props"].get("syllables") for r in stored] == [True, True]


def test_a_linked_lineatur_prints_its_bows(browser, server):
    client = user()
    mine = sheet(
        client,
        [box("lined", "ruling", {**RULING, "list": "copy", "syllables": True})],
        words=WORDS,
    )["id"]
    token = {"X-Render-Token": pdf.new_token(mine)}
    context = browser.new_context(
        viewport={"width": 1400, "height": 1000}, extra_http_headers=token
    )
    context.add_init_script("localStorage.setItem('tour', '1')")
    context.add_cookies([{"name": "session", "value": client.cookies["session"], "url": server}])
    page = context.new_page()
    page.goto(f"{server}/druck/{mine}")
    page.wait_for_selector("body.ready", state="attached")
    expect(page.locator(".syl").first).to_be_attached()
    context.close()
