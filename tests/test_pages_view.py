"""The page in use follows the desk's view: a new block lands on the page the teacher scrolls to."""

from playwright.sync_api import expect
from ui import TEXT, box, doc, insert, user

# The counter floats over the desk in the leaf theme, on a wide window.
COUNTER = ".dock.at"


def wheel(page, delta):
    """Turns the wheel over the middle of the desk, as a mouse does."""
    spot = page.locator(".desk").bounding_box()
    page.mouse.move(spot["x"] + spot["width"] / 2, spot["y"] + spot["height"] / 2)
    page.mouse.wheel(0, delta)


def add_text(page, word):
    """Clicks Text in the dock and types a word into the block it makes."""
    page.get_by_label("Text", exact=True).click()
    expect(page.locator(".block.sel .ProseMirror")).to_be_focused()
    page.keyboard.type(word)


def texts(saved_doc, n):
    """The words of the text blocks on page n."""
    return [b["props"]["text"] for b in saved_doc["pages"][n]["blocks"] if b["type"] == "text"]


def test_a_text_lands_on_the_page_the_wheel_brings_into_view(editor):
    """#579: page 3 fills the view, the counter says so, and the text lands there."""
    client = user()
    rest = [{"blocks": [box(name, "text", TEXT)]} for name in "bc"]
    page = editor(box("a", "text", TEXT), pages=rest, theme="leaf", client=client)
    wheel(page, 5000)
    expect(page.locator(COUNTER)).to_have_text("Seite 3 von 3")
    add_text(page, "Wort")
    saved_doc = doc(page, client)
    assert texts(saved_doc, 2) == ["Hallo", "Wort"]
    assert texts(saved_doc, 0) == ["Hallo"]


def test_a_text_lands_on_page_2_of_a_two_page_sheet_scrolled_to_it(editor):
    """#579 with two pages: the second one is in view and gets the text."""
    client = user()
    rest = [{"blocks": [box("b", "text", TEXT)]}]
    page = editor(box("a", "text", TEXT), pages=rest, theme="leaf", client=client)
    wheel(page, 5000)
    expect(page.locator(COUNTER)).to_have_text("Seite 2 von 2")
    add_text(page, "Wort")
    saved_doc = doc(page, client)
    assert texts(saved_doc, 1) == ["Hallo", "Wort"]
    assert texts(saved_doc, 0) == ["Hallo"]


def test_a_text_lands_on_page_1_after_the_wheel_brings_page_1_back(editor):
    """#579: scrolled down to page 3 and back up, the text lands on page 1 again."""
    client = user()
    rest = [{"blocks": [box(name, "text", TEXT)]} for name in "bc"]
    page = editor(box("a", "text", TEXT), pages=rest, theme="leaf", client=client)
    wheel(page, 5000)
    expect(page.locator(COUNTER)).to_have_text("Seite 3 von 3")
    wheel(page, -5000)
    expect(page.locator(COUNTER)).to_have_text("Seite 1 von 3")
    add_text(page, "Wort")
    saved_doc = doc(page, client)
    assert texts(saved_doc, 0) == ["Hallo", "Wort"]
    assert texts(saved_doc, 2) == ["Hallo"]


def test_typing_goes_on_while_the_wheel_scrolls_to_another_page(editor):
    """#579 review: a text being typed keeps its page and its focus when the wheel brings the next
    page into view; the next keys still go into it."""
    client = user()
    rest = [{"blocks": [box("b", "text", TEXT)]}]
    page = editor(box("a", "text", TEXT), pages=rest, theme="leaf", client=client)
    add_text(page, "Erst")
    wheel(page, 5000)
    page.keyboard.type("dann")
    expect(page.locator(".block.sel .ProseMirror")).to_have_text("Erstdann")
    expect(page.locator(COUNTER)).to_have_text("Seite 1 von 2")


def test_a_maths_block_from_the_dock_lands_on_the_page_in_view(editor):
    """#579: an item of "Mathe-Blöcke" lands on page 2 with page 2 in view, as a text does."""
    client = user()
    rest = [{"blocks": [box("b", "text", TEXT)]}]
    page = editor(box("a", "text", TEXT), pages=rest, theme="leaf", client=client)
    wheel(page, 5000)
    expect(page.locator(COUNTER)).to_have_text("Seite 2 von 2")
    insert(page, "Zahlenstrahl")
    expect(page.locator(".block.sel")).to_have_count(1)
    saved_doc = doc(page, client)
    kinds = [[b["type"] for b in p["blocks"]] for p in saved_doc["pages"]]
    assert kinds == [["text"], ["text", "zahlenstrahl"]]
