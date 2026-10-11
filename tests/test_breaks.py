"""A break set by hand holds for a word spelled with composed or decomposed letters (issue #386).

"Bären" has an "ä" that is one letter, U+00E4, or an "a" and U+0308. The panel lists the word once,
and a break set for one spelling cuts both.
"""

from playwright.sync_api import expect
from test_painter import held
from test_syllables import bows, gap, word
from ui import TEXT, box, pick, user

COMPOSED = "Bären"
DECOMPOSED = "Bären"
# The key the word is stored under: the composed spelling in lower case.
KEY = "bären"
# The key a break set before the fix is stored under: the decomposed spelling in lower case.
OLD_KEY = "bären"
BOTH = {**TEXT, "text": f"{COMPOSED} {DECOMPOSED}", "syllables": True}


def test_a_break_set_by_hand_holds_for_the_composed_and_the_decomposed_word(editor):
    client = user()
    page = editor(box("a", "text", BOTH), client=client)
    pick(page, "a")
    # The word is listed once, as its composed spelling has it.
    expect(page.locator(".panel .words button")).to_have_text(["Bä·ren"])
    word(page, "Bä·ren").click()
    # The module cuts "Bä|ren"; the click takes that away, and one after "Bär" is set.
    gap(page, "Bä|ren").click()
    gap(page, "Bär|en").click()
    expect(gap(page, "Bär|en")).to_have_attribute("aria-pressed", "true")
    expect(page.locator(".panel .words button")).to_have_text(["Bär·en"])
    # Both spellings are cut after "Bär", each at its own place in the text.
    bows(page, "a").to_have_text(["Bär", "en", "Bär", "en"])
    # One entry, in letters, under the one key.
    assert held(page, client)["a"]["breaks"] == {KEY: [3]}


def test_a_split_stored_under_the_old_decomposed_key_still_cuts_the_word(editor):
    text = {**TEXT, "text": DECOMPOSED, "syllables": True, "breaks": {OLD_KEY: [3]}}
    page = editor(box("a", "text", text))
    bows(page, "a").to_have_text(["Bä", "ren"])
