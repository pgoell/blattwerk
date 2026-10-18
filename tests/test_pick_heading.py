"""The right panel's heading names what is picked (#802): one block by its name, a group as "Gruppe",
and a count of units in the words of their type. It never says "Felder" for a pick of blocks.
"""

import pytest
from playwright.sync_api import expect
from ui import LINE, RECT, RULING, TABLE, TEXT, block, box, maths, pick, picture, upload, user

WALL = {
    "base": 3,
    "count": 4,
    "columns": 4,
    "max": 20,
    "op": "+",
    "given": "base",
    "empty": False,
    "seed": 7,
}
SHAPES = {
    "text": ("text", TEXT),
    "shape": ("shape", RECT),
    "line": ("shape", LINE),
    "table": ("table", TABLE),
    "ruling": ("ruling", RULING),
    "zahlenmauer": ("zahlenmauer", WALL),
}


def make(kind, client, name, y):
    """A block of the kind, named `name`, at height `y` on page 1."""
    if kind == "image":
        made = {**picture(upload(client)), "id": name}
    elif kind == "maths":
        made = {**block("maths", y, 12, maths(client)), "id": name}
    else:
        block_type, props = SHAPES[kind]
        made = box(name, block_type, props)
    return {**made, "y": y}


def heading(page):
    return page.locator(".panel .what")


@pytest.mark.parametrize(
    ("kind", "plural"),
    [
        ("text", "Texte"),
        ("shape", "Formen"),
        ("line", "Linien"),
        ("image", "Bilder"),
        ("table", "Tabellen"),
        ("ruling", "Lineaturen"),
        ("maths", "Rechenblöcke"),
        ("zahlenmauer", "Zahlenmauern"),
    ],
    ids=["text", "shape", "line", "image", "table", "ruling", "maths", "zahlenmauer"],
)
def test_a5_each_type_has_its_plural(editor, kind, plural):
    """A5: two blocks of one type picked read as a count in that type's plural."""
    client = user()
    page = editor(
        make(kind, client, "a", 15),
        make(kind, client, "b", 105),
        client=client,
    )
    pick(page, "a", "b")
    expect(heading(page)).to_have_text(f"2 {plural}")


def test_a5_three_texts_read_3_texte(editor):
    """A5: three texts picked read as "3 Texte"."""
    page = editor(
        box("a", "text", TEXT, y=15), box("b", "text", TEXT, y=60), box("c", "text", TEXT, y=105)
    )
    pick(page, "a", "b", "c")
    expect(heading(page)).to_have_text("3 Texte")


def test_a6_mixed_types_read_n_bloecke(editor):
    """A6: blocks of different types picked read as "N Blöcke", never as "Felder"."""
    client = user()
    page = editor(
        make("text", client, "a", 15),
        make("shape", client, "b", 60),
        make("zahlenmauer", client, "c", 105),
        client=client,
    )
    pick(page, "a", "b", "c")
    expect(heading(page)).to_have_text("3 Blöcke")
    expect(heading(page)).not_to_contain_text("Felder")


def test_i4_a_group_reads_gruppe_and_counts_once(editor):
    """I4: a group picked whole is one unit, "Gruppe"; with a loose text added it is "2 Blöcke"."""
    page = editor(
        box("a", "text", TEXT, y=15, group=["g1"]),
        box("b", "text", TEXT, y=60, group=["g1"]),
        box("c", "text", TEXT, y=105, group=["g1"]),
        box("d", "text", TEXT, y=150),
    )
    at_a = page.locator('.block[data-id="a"]')
    at_a.click()
    expect(heading(page)).to_have_text("Gruppe")
    page.locator('.block[data-id="d"]').click(modifiers=["Shift"])
    expect(heading(page)).to_have_text("2 Blöcke")


def test_i5_shift_click_one_off_names_the_one_left(editor):
    """I5: shift-clicking a picked block off leaves one block, which reads by its own name."""
    page = editor(box("a", "text", TEXT, y=15), box("b", "shape", RECT, y=60))
    pick(page, "a", "b")
    expect(heading(page)).to_have_text("2 Blöcke")
    # The selected shape's handles cover it, so the click goes through them to the shape.
    page.locator('.block[data-id="b"]').click(modifiers=["Shift"], force=True)
    expect(heading(page)).to_have_text("Text")
