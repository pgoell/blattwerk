"""Textaufgaben (#832): insert from the maths menu, and the Lösungen fill a blank Rechnung and Antwort."""

from playwright.sync_api import expect
from ui import doc, insert, tool, user


def test_a_textaufgabe_is_inserted_and_the_key_fills_the_blank_parts(editor):
    """Insert and Lösungen (#832): two Sachaufgaben, the story and the question shown, the Rechnung
    and the Antwort filled only in the Lösungen. Neu würfeln changes the seed."""
    client = user()
    page = editor(client=client)
    insert(page, "Textaufgaben")
    expect(
        page.locator(".panel").get_by_role("heading", name="Textaufgaben", exact=True)
    ).to_be_visible()
    drawn = page.locator(".textaufgabe")
    expect(drawn.locator("article.task")).to_have_count(2)
    task = drawn.locator("article.task").first
    expect(task.locator("[data-part='text']")).not_to_have_text("")
    expect(task.locator("[data-part='frage']")).to_have_attribute("data-open", "yes")
    expect(task.locator("[data-part='rechnung']")).to_have_attribute("data-open", "no")
    expect(task.locator("[data-part='antwort']")).to_have_attribute("data-open", "no")
    expect(task.locator(".sketch")).to_have_count(0)
    tool(page, "Lösungen zeigen").click()
    expect(task.locator("[data-part='rechnung']")).to_have_attribute("data-open", "yes")
    expect(task.locator("[data-part='antwort'] .answer")).not_to_have_text("")
    stored = doc(page, client)
    block = next(b for b in stored["pages"][0]["blocks"] if b["type"] == "textaufgabe")
    assert block["props"]["themes"] == ["sach"]
    assert block["props"]["frage"] is True
    assert block["props"]["rechnung"] is False
    assert block["props"]["antwort"] is False
    seed = block["props"]["seed"]
    page.get_by_role("button", name="Neu würfeln").click()
    again = doc(page, client)
    rolled = next(b for b in again["pages"][0]["blocks"] if b["type"] == "textaufgabe")
    assert rolled["props"]["seed"] != seed
    assert {k: v for k, v in rolled["props"].items() if k != "seed"} == {
        k: v for k, v in block["props"].items() if k != "seed"
    }
