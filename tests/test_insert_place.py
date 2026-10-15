"""A new block goes under the page's lowest block, at its left edge, if there is room (#293)."""

import pytest
from playwright.sync_api import expect
from ui import TEXT, box, copy_text, doc, insert, pick, png, user

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
    blocks = doc(page, client)["pages"][0]["blocks"]
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


def test_an_insert_with_no_room_below_lands_as_before(editor):
    """#293: a Punkte block (12 mm) under a block ending at 270 mm would pass the margin at 282."""
    client = user()
    page = editor(box("low", "text", TEXT, y=260, h=10, w=180), client=client)
    add_by_button(page, "Punkte")
    block = new_block(page, client, {"low"})
    assert (block["x"], block["y"]) == (85, 15)


def test_pasted_words_land_as_before(editor):
    """#293: words pasted from another app keep the centred place at the top of the view."""
    client = user()
    page = editor(*TOP, client=client)
    copy_text(page, "Aus einer anderen App")
    page.keyboard.press("Control+v")
    blocks = doc(page, client)["pages"][0]["blocks"]
    block = next(b for b in blocks if b.get("props", {}).get("text") == "Aus einer anderen App")
    assert (block["x"], block["y"]) == (65, 15)


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
