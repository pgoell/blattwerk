"""An own Zahlenraum the generator refuses stays in the field and says so."""

from playwright.sync_api import expect
from test_maths_foot import (
    FOOT,
    asked,
    height,
    refusal,
)
from ui import (
    box,
    doc,
    maths,
    pick,
    user,
)


def test_a_refused_own_zahlenraum_shows_the_blocks_in_the_field(editor):
    """#479: a refused own Zahlenraum leaves the field the block's number, not the refused one."""
    client = user()
    props = maths(client, ops=["/"], max=100, count=12, columns=3, size=14, format="written")
    page = editor(
        box("m", "maths", props, y=FOOT - height(props) - 1, h=height(props)), client=client
    )
    pick(page, "m")
    page.get_by_label("Zahlenraum").select_option(label="Eigener")
    field = page.get_by_label("Größte Zahl")
    field.fill("100000")
    field.press("Enter")
    refusal(page)
    expect(field).to_be_focused()
    expect(field).to_have_value("100")


def test_a_refusal_that_comes_after_more_typing_leaves_the_field_as_typed(editor):
    """#479: the answer for 100000 comes after more typing: the field keeps what was typed."""
    client = user()
    props = maths(client, ops=["/"], max=100, count=12, columns=3, size=14, format="written")
    page = editor(
        box("m", "maths", props, y=FOOT - height(props) - 1, h=height(props)), client=client
    )
    pick(page, "m")
    page.get_by_label("Zahlenraum").select_option(label="Eigener")
    held = []
    page.route("**/api/maths", lambda route: held.append(route))
    field = page.get_by_label("Größte Zahl")
    with page.expect_request("**/api/maths"):
        field.fill("100000")
        field.press("Enter")
    # An empty field asks the server nothing: the answer for 100000 stays the last one.
    field.fill("")
    held[0].continue_()
    refusal(page)
    expect(field).to_be_focused()
    expect(field).to_have_value("")


def test_an_accepted_own_zahlenraum_keeps_what_was_typed_and_undo_shows_the_old(editor):
    """#479: a fitting own Zahlenraum keeps the typed number, and one undo shows the old one."""
    client = user()
    props = maths(client, ops=["/"], max=100, count=12, columns=3, size=14, format="written")
    page = editor(box("m", "maths", props, y=20, h=height(props)), client=client)
    pick(page, "m")
    page.get_by_label("Zahlenraum").select_option(label="Eigener")
    field = page.get_by_label("Größte Zahl")
    field.fill("1000")
    asked(lambda page: field.press("Enter"))(page)
    expect(field).to_have_value("1000")
    field.blur()
    pick(page, "m")
    page.keyboard.press("Control+z")
    expect(field).to_have_value("100")


def test_an_own_zahlenraum_above_the_limit_says_so_and_shows_the_used_number(editor):
    """#734: 50000000 is above the limit: a line says so, and Enter shows the number in use."""
    client = user()
    props = maths(client, ops=["+"], max=100, count=12, columns=3, size=14, format="written")
    page = editor(box("m", "maths", props, y=20, h=height(props)), client=client)
    pick(page, "m")
    page.get_by_label("Zahlenraum").select_option(label="Eigener")
    field = page.get_by_label("Größte Zahl")
    field.fill("50000000")
    expect(page.get_by_role("status").filter(has_text="Höchstens 1.000.000")).to_be_visible()
    field.press("Enter")
    stored = next(b for b in doc(page, client)["pages"][0]["blocks"] if b["id"] == "m")
    expect(field).to_have_value(str(stored["props"]["max"]))
    expect(page.get_by_role("status").filter(has_text="Höchstens 1.000.000")).to_have_count(0)


def test_an_own_zahlenraum_below_one_says_so(editor):
    """#734: 0 is below the limit: a line says so, and Enter shows the number the exercises use."""
    client = user()
    props = maths(client, ops=["+"], max=100, count=12, columns=3, size=14, format="written")
    page = editor(box("m", "maths", props, y=20, h=height(props)), client=client)
    pick(page, "m")
    page.get_by_label("Zahlenraum").select_option(label="Eigener")
    field = page.get_by_label("Größte Zahl")
    field.fill("0")
    expect(page.get_by_role("status").filter(has_text="Mindestens 1")).to_be_visible()
    field.fill("50")
    expect(page.get_by_role("status").filter(has_text="Mindestens 1")).to_have_count(0)
    asked(lambda page: field.press("Enter"))(page)
    field.fill("0")
    field.press("Enter")
    expect(field).to_have_value("50")
    expect(page.get_by_role("status").filter(has_text="Mindestens 1")).to_have_count(0)


def test_an_own_zahlenraum_with_a_decimal_says_so(editor):
    """#734: 12.5 is no Zahlenraum: a line says so, and the exercises keep theirs."""
    client = user()
    props = maths(client, ops=["+"], max=100, count=12, columns=3, size=14, format="written")
    page = editor(box("m", "maths", props, y=20, h=height(props)), client=client)
    pick(page, "m")
    page.get_by_label("Zahlenraum").select_option(label="Eigener")
    field = page.get_by_label("Größte Zahl")
    field.fill("12.5")
    expect(page.get_by_role("status").filter(has_text="Nur ganze Zahlen")).to_be_visible()
    field.press("Enter")
    expect(field).to_have_value("100")


def test_typing_past_the_limit_never_applies_its_first_digits(editor):
    """#743: typing 1500000 applies no digit on the way. Enter applies 5000, one undo gives 100."""
    client = user()
    props = maths(client, ops=["+"], max=100, count=12, columns=3, size=14, format="written")
    page = editor(box("m", "maths", props, y=20, h=height(props)), client=client)
    pick(page, "m")
    page.get_by_label("Zahlenraum").select_option(label="Eigener")
    field = page.get_by_label("Größte Zahl")
    field.select_text()
    field.press_sequentially("1500000")
    expect(page.get_by_role("status").filter(has_text="Höchstens 1.000.000")).to_be_visible()
    field.blur()
    expect(field).to_have_value("100")
    stored = next(b for b in doc(page, client)["pages"][0]["blocks"] if b["id"] == "m")
    assert stored["props"]["max"] == 100
    field.fill("5000")
    asked(lambda page: field.press("Enter"))(page)
    expect(field).to_have_value("5000")
    field.blur()
    pick(page, "m")
    page.keyboard.press("Control+z")
    expect(field).to_have_value("100")
