"""The Karofeld in the editor: typing, Enter, a shifted row, and the four Darstellungen."""

from playwright.sync_api import expect
from ui import doc, insert, user


def test_typing_steps_across_and_enter_steps_to_the_next_row(editor):
    """#831: one sign per square, a comma stays on the digit, Enter goes to the next row."""
    client = user()
    page = editor(client=client)
    insert(page, "Karofeld")
    page.locator(".karofeld rect.cell").first.click()
    for key in ("1", ",", "2", "Enter", "3"):
        page.keyboard.press(key)
    expect(page.locator(".karofeld text")).to_have_text(["1,", "2", "3"])
    cells = doc(page, client)["pages"][0]["blocks"][0]["props"]["cells"]
    assert cells[0][0] == {"sign": "1", "mark": ","}
    assert cells[0][1] == {"sign": "2"}
    assert cells[1][0] == {"sign": "3"}


def test_insert_sign_shifts_the_rest_of_the_row(editor):
    """#831: Zeichen einfügen shifts the signs to the right of the caret."""
    client = user()
    page = editor(client=client)
    insert(page, "Karofeld")
    page.locator(".karofeld rect.cell").first.click()
    page.keyboard.press("1")
    page.keyboard.press("2")
    page.locator(".karofeld rect.cell").first.click()
    page.locator(".panel").get_by_role("button", name="Zeichen einfügen").click()
    cells = doc(page, client)["pages"][0]["blocks"][0]["props"]["cells"]
    assert [sq.get("sign") for sq in cells[0][:3]] == [None, "1", "2"]
    assert cells[0][0] == {}


def test_each_look_draws_its_own_marks(editor):
    """#831: Karos, Kreise, Punktefeld and the isometric grid."""
    client = user()
    page = editor(client=client)
    insert(page, "Karofeld")
    field = page.locator(".karofeld")
    expect(field.locator("svg")).to_have_attribute("data-look", "karos")
    expect(field.locator("g.mesh line")).to_have_count(11 + 9)
    page.locator(".panel").get_by_label("Darstellung").select_option("kreise")
    expect(field.locator("circle.ring")).to_have_count(80)
    page.locator(".panel").get_by_label("Darstellung").select_option("punkte")
    expect(field.locator("circle.dot")).to_have_count(80)
    expect(field.locator("g.mesh")).to_have_count(0)
    page.locator(".panel").get_by_label("Darstellung").select_option("iso")
    expect(field.locator("svg")).to_have_attribute("data-look", "iso")
    expect(field.locator("g.mesh line")).not_to_have_count(0)
    expect(field.locator("circle")).to_have_count(0)
