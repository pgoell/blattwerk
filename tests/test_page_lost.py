"""#805: a new block lands on the page in view, after any way of getting there, and a new page or
another layout leaves every arrow and line on its page and at its place."""

import pytest
from playwright.sync_api import expect
from test_pages_many import menu_item
from ui import LINE, RECT, TEXT, box, doc, pick, thumb, user

ARROW = {**RECT, "kind": "arrow"}
# What the insert bar makes, by the label of its button, and the type it saves.
MADE = [
    ("Pfeil", "shape"),
    ("Linie", "shape"),
    ("Rechteck", "shape"),
    ("Text", "text"),
    ("Strecke", "shape"),
]


def kinds(saved):
    return [[b["type"] for b in p["blocks"]] for p in saved["pages"]]


def insert(page, label):
    page.locator(".insert").get_by_label(label, exact=True).click()
    page.keyboard.press("Escape")


def two(editor, client):
    """A box on page 1 and a text on page 2; page 1 is in use, the panel Seiten open."""
    return editor(
        box("r", "shape", RECT),
        pages=[{"blocks": [box("t", "text", TEXT)]}],
        client=client,
        theme="",
    )


def expect_out_of_view(page, n):
    """Page n has left the desk's view at the top or the bottom."""
    page.wait_for_function(
        f"""() => {{
            const v = document.querySelector('.desk').getBoundingClientRect();
            const r = document.querySelector('.sheet[data-page="{n}"]').getBoundingClientRect();
            return r.top >= v.bottom || r.bottom <= v.top;
        }}"""
    )


def zoomed_onto_page_two(page):
    """Wheels page 2 into the lower part of the view, then zooms in with Ctrl and the wheel over
    it until page 1 has left the view. A zoom is not the teacher's scroll."""
    desk = page.locator(".desk").bounding_box()
    page.mouse.move(desk["x"] + desk["width"] / 2, desk["y"] + desk["height"] / 2)
    page.mouse.wheel(0, 700)
    page.mouse.move(desk["x"] + desk["width"] / 2, desk["y"] + desk["height"] - 20)
    page.keyboard.down("Control")
    for _ in range(8):
        page.mouse.wheel(0, -100)
    page.keyboard.up("Control")
    expect_out_of_view(page, 0)


@pytest.mark.parametrize(("label", "kind"), MADE)
def test_a_block_lands_on_page_2_after_a_zoom_onto_it(editor, label, kind):
    """Zoomed in about page 2 with page 1 in use, page 1 out of view: the new block lands on page 2."""
    client = user()
    page = two(editor, client)
    zoomed_onto_page_two(page)
    insert(page, label)
    assert kinds(doc(page, client)) == [["shape"], ["text", kind]]


def test_a_block_lands_on_the_page_a_page_key_brings_with_a_block_picked(editor):
    """With the box on page 1 picked, the page keys bring page 2 into view: the arrow lands there."""
    client = user()
    page = two(editor, client)
    pick(page, "r")
    page.keyboard.press("End")
    expect_out_of_view(page, 0)
    insert(page, "Pfeil")
    assert kinds(doc(page, client)) == [["shape"], ["text", "shape"]]


def test_a_block_lands_on_page_1_scrolled_back_to_after_a_new_page(editor):
    """The teacher's report: a new page, then back to page 1 by a scroll the editor does not
    count as hers (here set by a script): the arrow lands on page 1, not on the new page."""
    client = user()
    page = two(editor, client)
    page.locator(".insert").get_by_label("Neue Seite", exact=True).click()
    expect(page.locator(".sheet[data-page]")).to_have_count(3)
    page.wait_for_function("() => document.querySelector('.desk').scrollTop > 500")
    page.evaluate("document.querySelector('.desk').scrollTop = 0")
    expect_out_of_view(page, 1)
    insert(page, "Pfeil")
    assert kinds(doc(page, client)) == [["shape", "shape"], [], ["text"]]


def test_a_text_opened_during_a_zoom_onto_page_2_hands_page_2_on_once_it_closes(editor):
    """A text open on page 1 keeps its page while a zoom takes page 1 out of view; after Escape the
    next block lands on page 2."""
    client = user()
    page = two(editor, client)
    page.locator(".insert").get_by_label("Text", exact=True).click()
    expect(page.locator(".block.sel .ProseMirror")).to_be_focused()
    page.keyboard.type("Erst")
    zoomed_onto_page_two(page)
    expect(page.locator(".block.sel .ProseMirror")).to_have_text("Erst")
    page.keyboard.press("Escape")
    insert(page, "Pfeil")
    assert kinds(doc(page, client)) == [["shape", "text"], ["text", "shape"]]


def test_a_thumbnail_click_puts_the_next_block_on_its_page(editor):
    """Control: a click on page 1's thumbnail after a new page brings page 1 back into use."""
    client = user()
    page = two(editor, client)
    page.locator(".insert").get_by_label("Neue Seite", exact=True).click()
    expect(thumb(page, 2)).to_be_visible()
    thumb(page, 0).click()
    insert(page, "Pfeil")
    assert kinds(doc(page, client)) == [["shape", "shape"], [], ["text"]]


def places(page, client):
    """Each block's page and place in the saved sheet, and its place on the screen in its page."""
    saved = doc(page, client)
    stored = {
        b["id"]: (n, b["x"], b["y"], b["w"], b["h"])
        for n, p in enumerate(saved["pages"])
        for b in p["blocks"]
    }
    shown = page.evaluate(
        """() => Object.fromEntries([...document.querySelectorAll('.desk .block[data-id]')].map((el) => {
            const s = el.closest('.sheet'), r = el.getBoundingClientRect(), q = s.getBoundingClientRect();
            return [el.dataset.id, [+s.dataset.page, (r.left - q.left) / q.width, (r.top - q.top) / q.height]];
        }))"""
    )
    return stored, {name: [n, round(x, 3), round(y, 3)] for name, (n, x, y) in shown.items()}


def lines(editor, client):
    arrow = {**box("p", "shape", ARROW), "w": 60, "h": 0, "y": 100}
    line = {**box("l", "shape", LINE), "w": 60, "h": 0, "y": 140}
    return editor(
        box("r", "shape", RECT),
        arrow,
        line,
        pages=[{"blocks": [box("t", "text", TEXT)]}],
        client=client,
        theme="",
    )


WAYS = {
    "neue Seite": lambda page: (
        page.locator(".insert").get_by_label("Neue Seite", exact=True).click()
    ),
    "eingefügte Seite": lambda page: (
        thumb(page, 0).click(button="right"),
        menu_item(page, "Neue Seite").click(),
    ),
}


@pytest.mark.parametrize("way", list(WAYS))
@pytest.mark.parametrize("chosen", [None, "p", "l"])
def test_a_new_page_leaves_every_arrow_and_line_at_its_place(editor, way, chosen):
    """An arrow and a line beside a box (the control), one of them picked or none: a page added after
    page 1 moves none of them, in the saved sheet or on the screen."""
    client = user()
    page = lines(editor, client)
    if chosen:
        pick(page, chosen)
    stored, shown = places(page, client)
    WAYS[way](page)
    expect(page.locator(".sheet[data-page]")).to_have_count(3)
    after_stored, after_shown = places(page, client)
    assert {k: v for k, v in after_stored.items() if k != "t"} == {
        k: v for k, v in stored.items() if k != "t"
    }
    assert after_stored["t"][0] == 2
    assert {k: v for k, v in after_shown.items() if k != "t"} == {
        k: v for k, v in shown.items() if k != "t"
    }


@pytest.mark.parametrize("chosen", [None, "p"])
@pytest.mark.parametrize("scope", ["Alle Seiten", "Nur diese Seite"])
def test_quer_and_hoch_leave_every_arrow_and_line_on_its_page_and_place(editor, chosen, scope):
    """The sheet, or page 1 alone, laid on its side and upright again: the arrow and the line stay
    on page 1, at their place, as the box does."""
    client = user()
    page = lines(editor, client)
    if chosen:
        pick(page, chosen)
    stored, _ = places(page, client)
    page.get_by_role("tab", name="Ansicht").click()
    panel = page.locator(".panel")
    panel.get_by_role("button", name=scope, exact=True).click()
    panel.get_by_role("button", name="Quer", exact=True).click()
    quer, _ = places(page, client)
    assert {k: (v[0], v[1], v[2]) for k, v in quer.items()} == {
        k: (v[0], v[1], v[2]) for k, v in stored.items()
    }
    panel.get_by_role("button", name="Hoch", exact=True).click()
    hoch, _ = places(page, client)
    assert hoch == stored
