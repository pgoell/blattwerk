"""The library "Mathe-Blöcke": a field over the sheet with a search box, groups and a picture of each block (#1183)."""

from playwright.sync_api import expect
from ui import doc, user

GROUPS = {
    "Rechenformate": 12,
    "Zahlen verstehen": 7,
    "Geometrie und Größen": 4,
    "Knobeln und Kontrolle": 3,
}


def library(page):
    """Opens the library from its button and gives the field."""
    page.locator(".dock, .insert").get_by_label("Mathe-Blöcke", exact=True).click()
    field = page.locator("dialog.library")
    expect(field).to_be_visible()
    return field


def names(field):
    """The names of the cards that show, in their order."""
    return field.locator(".card").evaluate_all("els => els.map((el) => el.ariaLabel)")


def kinds(page, client):
    return [b["type"] for b in doc(page, client)["pages"][0]["blocks"]]


def test_the_26_blocks_stand_in_groups_each_with_a_picture_of_the_block(editor):
    """The blocks stand under four headings, and each card holds its block drawn small."""
    page = editor(client=user())
    field = library(page)
    for name, count in GROUPS.items():
        group = field.get_by_role("region", name=name, exact=True)
        expect(group.get_by_role("heading", name=name, exact=True)).to_be_visible()
        expect(group.locator(".card")).to_have_count(count)
    expect(field.locator(".card")).to_have_count(26)
    expect(field.locator(".card .pic .block")).to_have_count(26)
    # A picture is the block itself: the wall has its stones, the clock its hands.
    assert field.get_by_label("Zahlenmauer", exact=True).locator(".pic .block *").count() > 10
    assert field.get_by_label("Uhr", exact=True).locator(".pic svg").count() > 0
    # The field lies over the sheet, to the right of the list of tools.
    tools = page.locator(".insert").bounding_box()
    box = field.bounding_box()
    assert box["x"] >= tools["x"] + tools["width"]
    assert box["width"] >= 500


def test_the_search_finds_a_block_by_its_name_and_by_other_words(editor):
    """ "Uhr" finds the clock, a word that is not in a name finds its block, and nothing found says so."""
    page = editor(client=user())
    field = library(page)
    search = field.get_by_label("Block suchen")
    search.fill("Uhr")
    expect(field.locator(".card")).to_have_count(1)
    expect(field.get_by_label("Uhr", exact=True)).to_be_visible()
    search.fill("uhrzeit")
    expect(field.locator(".card")).to_have_count(len(["Uhr"]))
    assert names(field) == ["Uhr"]
    search.fill("sachaufgabe")
    expect(field.locator(".card")).to_have_count(len(["Textaufgaben"]))
    assert names(field) == ["Textaufgaben"]
    search.fill("stellenwert")
    expect(field.locator(".card")).to_have_count(
        len(["Stellenwert-Bild", "Stellenwerttafel", "Zahlzerlegung"])
    )
    assert names(field) == ["Stellenwert-Bild", "Stellenwerttafel", "Zahlzerlegung"]
    search.fill("xyz")
    expect(field.locator(".card")).to_have_count(0)
    expect(field.get_by_role("status")).to_contain_text("Kein Block passt")
    search.fill("")
    expect(field.locator(".card")).to_have_count(26)


def test_one_click_adds_the_block_and_shuts_the_field(editor):
    """A click on a card adds its block and shuts the library; the block is selected."""
    client = user()
    page = editor(client=client)
    library(page).get_by_label("Zahlenhaus", exact=True).click()
    expect(page.locator("dialog.library")).not_to_be_visible()
    expect(
        page.locator(".panel").get_by_role("heading", name="Zahlenhaus", exact=True)
    ).to_be_visible()
    assert kinds(page, client) == ["zahlenhaus"]


def test_a_click_beside_the_field_shuts_it_and_adds_nothing(editor):
    """A click outside shuts the library, and the button opens it again."""
    client = user()
    page = editor(client=client)
    field = library(page)
    box = field.bounding_box()
    page.mouse.click(box["x"] + box["width"] + 40, box["y"] + 40)
    expect(field).not_to_be_visible()
    assert kinds(page, client) == []
    expect(library(page).locator(".card")).to_have_count(26)


def test_the_keys_the_focus_is_in_the_search_box_arrows_walk_the_cards_and_enter_adds(editor):
    """The focus lands in the search box; the arrows move the mark through the cards and Enter adds the marked one."""
    client = user()
    page = editor(client=client)
    field = library(page)
    expect(field.get_by_label("Block suchen")).to_be_focused()
    marked = field.locator(".card[aria-current=true]")
    expect(marked).to_have_attribute("aria-label", "Zahlenmauer")
    page.keyboard.press("ArrowRight")
    expect(marked).to_have_attribute("aria-label", "Zahlenhaus")
    # Down goes to the card below, in the next row of four.
    page.keyboard.press("ArrowDown")
    expect(marked).to_have_attribute("aria-label", "Rechentabelle")
    page.keyboard.press("ArrowLeft")
    expect(marked).to_have_attribute("aria-label", "Rechenrad")
    page.keyboard.press("ArrowUp")
    expect(marked).to_have_attribute("aria-label", "Zahlenmauer")
    page.keyboard.press("End")
    expect(marked).to_have_attribute("aria-label", "Lösungsfeld")
    expect(marked).to_be_in_viewport()
    page.keyboard.press("Home")
    page.keyboard.press("ArrowRight")
    page.keyboard.press("Enter")
    expect(field).not_to_be_visible()
    assert kinds(page, client) == ["zahlenhaus"]


def test_enter_adds_the_first_block_the_search_found(editor):
    """Typing and Enter is enough: the first card found is the marked one."""
    client = user()
    page = editor(client=client)
    library(page)
    page.keyboard.type("uhr")
    page.keyboard.press("Enter")
    expect(page.locator("dialog.library")).not_to_be_visible()
    assert kinds(page, client) == ["uhr"]


def test_the_same_library_opens_on_the_tablet(editor):
    """On the iPad held upright the library opens beside the rail, inside the window, and a tap adds."""
    client = user()
    page = editor(client=client, touch=True)
    page.locator(".rail").get_by_label("Mathe", exact=True).tap()
    field = page.locator("dialog.library")
    expect(field.locator(".card")).to_have_count(26)
    box = field.bounding_box()
    window = page.viewport_size
    assert box["x"] >= 0 and box["x"] + box["width"] <= window["width"]
    assert box["y"] >= 0 and box["y"] + box["height"] <= window["height"]
    field.get_by_label("Geobrett", exact=True).tap()
    expect(field).not_to_be_visible()
    assert kinds(page, client) == ["geobrett"]
