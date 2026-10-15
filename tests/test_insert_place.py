"""A new block goes under the page's lowest block, at its left edge, if there is room (#293)."""

import pytest
from playwright.sync_api import expect
from test_clipboard import no_picture
from test_delete_page_zoom import quer
from test_words import list_tab, rulings
from test_zoom import wheel
from ui import TEXT, at, box, copy_picture, copy_text, doc, insert, pick, png, user

# A name line at the top, and a heading under it: the new block goes under the heading, 5 mm lower.
NAME = box("name", "name", {}, y=15, h=10, w=180)
HEAD = {**TEXT, "text": "Kopf", "size": 24, "bold": True}
HEADING = box("heading", "text", HEAD, y=32, h=14, w=180)
TOP = [NAME, HEADING]


def dock(page, label):
    return page.locator(".dock, .insert").get_by_label(label, exact=True)


def new_block(page, client, before):
    """The block the insert added: the one not on the page before. A maths block or a picture
    comes from the server, so this waits until the block is drawn."""
    count = len(before) + 1
    drawn = "document.querySelectorAll('.sheet .block[data-id]').length"
    page.wait_for_function(f"{drawn} === {count}")
    blocks = [b for p in doc(page, client)["pages"] for b in p["blocks"]]
    fresh = [b for b in blocks if b["id"] not in before]
    assert len(fresh) == 1, blocks
    return fresh[0]


def add_by_button(page, label):
    dock(page, label).click()


def add_by_menu(page, label):
    insert(page, label)


def add_by_file(page, label):
    picture = {"name": "bild.png", "mimeType": "image/png", "buffer": png()}
    page.locator("input[type=file]").set_input_files(picture)


# Each insert by the button a teacher presses: how to press it, and the button's label.
INSERTS = {
    "Text": (add_by_button, "Text"),
    "Ueberschrift": (add_by_button, "Überschrift"),
    "Tabelle": (add_by_button, "Tabelle"),
    "Lineatur": (add_by_button, "Lineatur"),
    "Namenszeile": (add_by_button, "Namenszeile"),
    "Punkte": (add_by_button, "Punkte"),
    "Suchsel": (add_by_button, "Suchsel"),
    "Symbol": (add_by_button, "Symbol"),
    "Strecke": (add_by_button, "Strecke"),
    "Zahlenmauer": (add_by_menu, "Zahlenmauer"),
    "Rechendreieck": (add_by_menu, "Rechendreieck"),
    "Zahlenstrahl": (add_by_menu, "Zahlenstrahl"),
    "Hunderterfeld": (add_by_menu, "Hunderterfeld"),
    "Uhr": (add_by_menu, "Uhr"),
    "Selbstkontrolle": (add_by_menu, "Selbstkontrolle"),
    "Rechteck": (add_by_button, "Rechteck"),
    "Rechnen": (add_by_button, "Rechnen"),
    "Bild": (add_by_file, "Bild"),
}


@pytest.mark.parametrize("what", list(INSERTS))
def test_an_insert_goes_under_the_lowest_block_at_its_left_edge(editor, what):
    """#293: the heading ends at 46 mm, so the new block starts at 51 mm, at the name's edge."""
    client = user()
    page = editor(*TOP, client=client)
    press, label = INSERTS[what]
    press(page, label)
    block = new_block(page, client, {"name", "heading"})
    assert (block["x"], block["y"]) == (15, 51)


def test_an_insert_with_no_room_below_takes_the_first_free_spot(editor):
    """#630: a Punkte block (12 mm) under a block ending at 270 mm would pass the margin at 282,
    so it takes the first free spot of the page, the top-left margin."""
    client = user()
    page = editor(box("low", "text", TEXT, y=260, h=10, w=180), client=client)
    add_by_button(page, "Punkte")
    block = new_block(page, client, {"low"})
    assert (block["x"], block["y"]) == (15, 15)


def test_pasted_words_land_as_before(editor):
    """#293: words pasted from another app keep the centred place at the top of the view."""
    client = user()
    page = editor(*TOP, client=client)
    copy_text(page, "Aus einer anderen App")
    page.keyboard.press("Control+v")
    blocks = doc(page, client)["pages"][0]["blocks"]
    block = next(b for b in blocks if b.get("props", {}).get("text") == "Aus einer anderen App")
    assert (block["x"], block["y"]) == (65, 15)


@no_picture
def test_a_pasted_picture_lands_as_before(editor):
    """#293: a picture pasted from another app keeps the place at the top of the view too."""
    client = user()
    page = editor(*TOP, client=client)
    copy_picture(page)
    page.keyboard.press("Control+v")
    block = new_block(page, client, {"name", "heading"})
    assert block["type"] == "image"
    assert block["y"] == 15


def test_an_insert_goes_under_a_turned_block_as_it_stands(editor):
    """#293: a text turned upright fills 15 to 195 mm down the page: the table goes under that."""
    client = user()
    page = editor(box("up", "text", TEXT, x=15, y=100, w=180, h=10, angle=90), client=client)
    add_by_button(page, "Tabelle")
    block = new_block(page, client, {"up"})
    assert (block["x"], block["y"]) == (15, 200)


def test_an_insert_on_an_empty_page_lands_as_before(editor):
    """#293: with no block to go under, the block comes centred to the top of the view."""
    client = user()
    page = editor(client=client)
    add_by_button(page, "Punkte")
    block = new_block(page, client, set())
    assert (block["x"], block["y"]) == (85, 15)


def test_an_insert_while_a_block_is_picked_takes_the_same_spot(editor):
    """#293: a picked block changes nothing about the spot, and the new block is the one picked."""
    client = user()
    page = editor(*TOP, client=client)
    pick(page, "heading")
    add_by_button(page, "Punkte")
    block = new_block(page, client, {"name", "heading"})
    assert (block["x"], block["y"]) == (15, 51)
    expect(page.locator(".block.sel")).to_have_attribute("data-id", block["id"])


def test_an_insert_under_a_block_at_the_right_stays_on_the_page(editor):
    """#293: the lowest block sits at the right, so a wide table moves left onto the page."""
    client = user()
    page = editor(box("right", "text", TEXT, x=100, y=100, h=10, w=100), client=client)
    add_by_button(page, "Tabelle")
    block = new_block(page, client, {"right"})
    assert (block["x"], block["y"]) == (15, 115)


def test_the_knickblatt_button_goes_under_the_lowest_block(editor):
    """#293: the Knickblatt is 180 mm wide and six rows high, and lands 5 mm under the heading."""
    client = user()
    page = editor(*TOP, client=client, theme="", words=["Hund", "Katze", "Maus"])
    list_tab(page)
    page.get_by_role("button", name="Knickblatt", exact=True).click()
    [blatt] = rulings(doc(page, client))
    assert (blatt["x"], blatt["y"]) == (15, 51)


def test_a_block_under_the_view_is_brought_into_it(editor):
    """#293: a block that lands below the visible part of the desk is scrolled into view."""
    client = user()
    page = editor(box("low", "text", TEXT, x=15, y=200, h=14, w=180), client=client)
    wheel(page, -300)
    page.locator(".desk").evaluate("d => (d.scrollTop = 0)")
    expect(at(page, "low")).not_to_be_in_viewport()
    add_by_button(page, "Punkte")
    block = new_block(page, client, {"low"})
    assert (block["x"], block["y"]) == (15, 219)
    expect(at(page, block["id"])).to_be_in_viewport()


def drawn_overlaps(page, id):
    """The ids of the blocks whose drawn boxes on the page cross the block's, in the browser."""
    return page.evaluate(
        """(id) => {
          const box = (el) => {
            const r = el.getBoundingClientRect();
            return [r.left, r.top, r.right, r.bottom];
          };
          const me = document.querySelector(`.sheet .block[data-id="${id}"]`);
          const [a, b, c, d] = box(me);
          return [...me.closest('.sheet').querySelectorAll('.block[data-id]')]
            .filter((el) => el !== me)
            .filter((el) => {
              const [l, t, r, u] = box(el);
              return a < r - 1 && l < c - 1 && b < u - 1 && t < d - 1;
            })
            .map((el) => el.dataset.id);
        }""",
        id,
    )


def page_of(client, page, id):
    """The number of the page that holds the block, counted from 0."""
    pages = doc(page, client)["pages"]
    return next(i for i, p in enumerate(pages) if any(b["id"] == id for b in p["blocks"]))


# A block from 50 mm to the margin, under the name and heading: no room for a 100 mm square.
FULL = box("full", "text", TEXT, x=15, y=50, h=200, w=180)


def test_a_full_page_puts_the_block_on_the_next_page_not_over_the_top(editor):
    """#630: no spot on page 1 for a Hunderterfeld, so it lands on page 2 at the top-left margin."""
    client = user()
    page = editor(*TOP, FULL, client=client)
    add_by_menu(page, "Hunderterfeld")
    block = new_block(page, client, {"name", "heading", "full"})
    assert page_of(client, page, block["id"]) == 1
    assert (block["x"], block["y"]) == (15, 15)
    assert drawn_overlaps(page, block["id"]) == []


def test_a_quer_page_puts_a_kreis_in_its_free_third(editor):
    """#630: on a Quer page the blocks fill the left, so a Kreis lands in the free right part."""
    client = user()
    # 150 mm wide, so that Quer does not stretch them over the page.
    head = box("head", "text", HEAD, x=15, y=15, h=14, w=150)
    body = box("body", "text", TEXT, x=15, y=40, h=150, w=150)
    page = editor(head, body, client=client, theme="")
    quer(page, 0)
    dock(page, "Kreis").click()
    block = new_block(page, client, {"head", "body"})
    assert page_of(client, page, block["id"]) == 0
    assert block["x"] >= 170
    assert drawn_overlaps(page, block["id"]) == []


def test_every_page_full_takes_a_new_page_and_one_undo_takes_both(editor):
    """#630: every page full: the block comes on a new page 3, and one Ctrl+Z takes both."""
    client = user()
    full2 = box("full2", "text", TEXT, x=15, y=50, h=200, w=180)
    page = editor(FULL, pages=[{"blocks": [full2]}], client=client)
    add_by_menu(page, "Hunderterfeld")
    block = new_block(page, client, {"full", "full2"})
    assert page_of(client, page, block["id"]) == 2
    assert (block["x"], block["y"]) == (15, 15)
    page.keyboard.press("Control+z")
    pages = doc(page, client)["pages"]
    assert len(pages) == 2
    assert all(b["id"] != block["id"] for p in pages for b in p["blocks"])


def test_a_turned_block_counts_by_the_box_it_fills(editor):
    """#630: a text turned upright fills 100 to 110 mm across: a Punkte goes under it."""
    client = user()
    page = editor(box("up", "text", TEXT, x=15, y=100, w=180, h=10, angle=90), client=client)
    add_by_button(page, "Punkte")
    block = new_block(page, client, {"up"})
    assert (block["x"], block["y"]) == (100, 200)
    assert drawn_overlaps(page, block["id"]) == []
