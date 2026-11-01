"""Sonderzeichen in the text bar: a fixed set, a Unicode code, and the last ones used.

The menu sits in the Schrift section. A click puts the character at the caret of an open
text, in that text's font, and a text that is only selected gains it at the end.
"""

import re

from playwright.sync_api import expect
from ui import FIELD, TEXT, at, box, pick

TIMES = "\u00d7"
DOT = "\u00b7"
EURO = "\u20ac"
GRUND = {**TEXT, "font": "grund"}


def test_a_symbol_from_the_text_bar_lands_in_the_text(editor):
    page = editor(box("a", "text", GRUND))
    pick(page, "a")
    page.keyboard.press("Enter")
    page.keyboard.press("End")
    page.get_by_role("button", name="Sonderzeichen", exact=True).click()
    marks = page.get_by_role("group", name="Zeichen")
    mal = marks.get_by_role("button", name="Mal", exact=True)
    expect(mal).to_have_css("font-family", re.compile(r"Playwrite DE Grund"))
    mal.click()
    field = page.locator(FIELD)
    expect(field).to_be_focused()
    expect(field).to_have_text("Hallo" + TIMES)

    code = page.get_by_label("Unicode", exact=True)
    code.fill("U+00B7")
    preview = page.get_by_label("Vorschau", exact=True)
    expect(preview).to_have_text(DOT)
    expect(preview).to_have_css("font-family", re.compile(r"Playwrite DE Grund"))
    page.get_by_role("button", name="Zeichen einfügen", exact=True).click()
    expect(field).to_be_focused()
    expect(field).to_have_text("Hallo" + TIMES + DOT)
    expect(page.get_by_role("group", name="Zuletzt").get_by_role("button")).to_have_text(
        [DOT, TIMES]
    )

    code.fill("U+0000")
    expect(preview).to_have_text("")
    expect(page.get_by_role("button", name="Zeichen einfügen", exact=True)).to_be_disabled()

    # The code field has the focus, so Rückgängig ends the writing, as any header button does.
    # The dot is gone. The text is only selected now, and Euro is added at its end.
    page.get_by_label("Rückgängig", exact=True).click()
    expect(page.locator(".ProseMirror")).to_have_count(0)
    expect(at(page, "a")).to_contain_text("Hallo" + TIMES)
    expect(at(page, "a")).not_to_contain_text(DOT)
    marks.get_by_role("button", name="Euro", exact=True).click()
    expect(at(page, "a")).to_contain_text("Hallo" + TIMES + EURO)
