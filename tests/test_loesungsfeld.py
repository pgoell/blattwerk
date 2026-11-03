"""A Lösungsfeld is blank on the pupil's sheet. The Lösungen print its text or its picture.

The line of an even field is as wide as the longest answer, so the length gives nothing away.
"""

from playwright.sync_api import expect
from test_gaps import step
from ui import box, doc, insert, pick, png, tool, upload, user

BASE = {"kind": "text", "text": "Hund", "blank": "line", "size": 14, "even": False}


def field(name, props, z=1):
    return box(name, "loesungsfeld", props, z=z, h=14)


def blank(page, name):
    return page.locator(f'.block[data-id="{name}"] .blank')


def width(page, name):
    box_ = blank(page, name).bounding_box()
    assert box_
    return box_["width"]


def test_the_text_is_blank_until_the_loesungen(editor):
    """A Lösungstext is absent on the sheet and printed once Lösungen zeigen is on."""
    page = editor(field("a", BASE))
    root = page.locator('.block[data-id="a"] .loesungsfeld')
    expect(root).to_have_attribute("data-blank", "line")
    expect(root.locator(".answer")).to_have_count(0)
    tool(page, "Lösungen zeigen").click()
    expect(root.locator(".answer")).to_have_text("Hund")


def test_the_blank_can_be_a_frame_or_nothing(editor):
    """Rahmen and Nichts are the other two blanks. The answer still waits for the Lösungen."""
    page = editor(field("a", {**BASE, "blank": "box"}), field("b", {**BASE, "blank": "none"}, z=2))
    expect(page.locator('.block[data-id="a"] .loesungsfeld')).to_have_attribute("data-blank", "box")
    expect(page.locator('.block[data-id="b"] .loesungsfeld')).to_have_attribute(
        "data-blank", "none"
    )
    expect(page.locator(".loesungsfeld .answer")).to_have_count(0)


def test_the_picture_shows_only_in_the_loesungen(editor):
    """A Lösungsbild is a symbol from the library, hidden until the Lösungen."""
    page = editor(field("a", {**BASE, "kind": "image", "code": "1F333", "text": ""}))
    root = page.locator(".loesungsfeld")
    expect(root.locator("img")).to_have_count(0)
    tool(page, "Lösungen zeigen").click()
    expect(root.locator("img[src='/openmoji/1F333.svg']")).to_have_count(1)


def test_an_uploaded_picture_shows_only_in_the_loesungen(editor):
    """An uploaded picture is hidden on the sheet and shown in the Lösungen."""
    client = user()
    pic = upload(client)
    page = editor(
        field("a", {**BASE, "kind": "image", "upload": pic, "ratio": 1.5, "text": ""}),
        client=client,
    )
    root = page.locator(".loesungsfeld")
    expect(root.locator("img")).to_have_count(0)
    tool(page, "Lösungen zeigen").click()
    expect(root.locator(f"img[src='/api/uploads/{pic}']")).to_have_count(1)


def test_the_panel_stores_an_uploaded_picture(editor, tmp_path):
    """Eigenes Bild uploads a picture and the Lösungen are where it shows."""
    client = user()
    path = tmp_path / "bild.png"
    path.write_bytes(png())
    page = editor(field("a", {**BASE, "kind": "image", "text": ""}), client=client)
    pick(page, "a")
    with page.expect_response(lambda res: res.request.method == "PATCH") as saved:
        page.locator(".panel").get_by_label("Eigenes Bild").set_input_files(path)
    assert saved.value.ok
    props = next(b["props"] for b in doc(page, client)["pages"][0]["blocks"] if b["id"] == "a")
    assert isinstance(props["upload"], int)
    expect(page.locator(".loesungsfeld img")).to_have_count(0)
    tool(page, "Lösungen zeigen").click()
    expect(page.locator(f"img[src='/api/uploads/{props['upload']}']")).to_have_count(1)


def test_even_fields_share_the_longest_answer(editor):
    """Alle Lösungsfelder gleich breit: the short line grows to the long one."""
    page = editor(
        field("a", {**BASE, "text": "Ja", "even": True}),
        field("b", {**BASE, "text": "Elefant", "even": True}, z=2),
        field("c", {**BASE, "text": "Ja"}, z=3),
        field("d", {**BASE, "text": "Schmetterling"}, z=4),
    )
    assert abs(width(page, "a") - width(page, "b")) < 2
    assert width(page, "c") < width(page, "d") - 8


def test_the_panel_stores_the_text_the_frame_and_the_wrong_answers(editor):
    """The panel writes the Lösungstext, the blank and one falsche Lösung per line."""
    client = user()
    page = editor(field("a", {**BASE, "text": ""}), client=client)
    pick(page, "a")
    panel = page.locator(".panel")
    panel.get_by_label("Lösungstext", exact=True).fill("Hund")
    panel.get_by_label("Leerfeld", exact=True).select_option("box")
    step(page, lambda: panel.get_by_label("Falsche Lösungen", exact=True).fill("Katze\nMaus"))
    props = next(b["props"] for b in doc(page, client)["pages"][0]["blocks"] if b["id"] == "a")
    assert props["text"] == "Hund"
    assert props["blank"] == "box"
    assert props["wrongs"] == [
        {"kind": "text", "text": "Katze"},
        {"kind": "text", "text": "Maus"},
    ]


def test_the_checkbox_evens_every_field_on_the_page(editor):
    """The checkbox sets even on every Lösungsfeld of the page, and the lines match."""
    client = user()
    page = editor(
        field("a", {**BASE, "text": "Ja"}),
        field("b", {**BASE, "text": "Elefant"}, z=2),
        client=client,
    )
    pick(page, "a")
    step(
        page, lambda: page.locator(".panel").get_by_label("Alle Lösungsfelder gleich breit").click()
    )
    blocks = {b["id"]: b["props"] for b in doc(page, client)["pages"][0]["blocks"]}
    assert blocks["a"]["even"] is True
    assert blocks["b"]["even"] is True
    assert abs(width(page, "a") - width(page, "b")) < 1


def test_the_menu_adds_a_blank_loesungstext(editor):
    """Mathe-Blöcke adds a Lösungsfeld with an empty Lösungstext and an underline."""
    client = user()
    page = editor(client=client)
    insert(page, "Lösungsfeld")
    expect(
        page.locator(".panel").get_by_role("heading", name="Lösungsfeld", exact=True)
    ).to_be_visible()
    [block] = doc(page, client)["pages"][0]["blocks"]
    assert block["type"] == "loesungsfeld"
    assert block["props"] == {
        "kind": "text",
        "text": "",
        "blank": "line",
        "size": 14,
        "even": False,
    }
