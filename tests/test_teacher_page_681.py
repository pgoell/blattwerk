"""The teacher-page faults from issue #681 that the sixteenth run hit."""

# The fixtures imported below are named again as a test's arguments.
# ruff: noqa: F811

from playwright.sync_api import expect
from test_clipboard import blocks
from test_drop import WEB_PICTURE, spot
from test_menu import menu
from test_pages import three
from test_teacher_page import folder, pytestmark, tool, xy  # noqa: F401
from ui import TEXT, at, box, png, saved, thumb, user

KEPT = "Deine Aufnahme lief noch, als das Formular zuging. Sie ist unten gespeichert."


def test_ctrl_click_adds_a_page_and_a_second_drops_it(editor):
    # The thumbnail's text is the page's own words too, so "Seite 1" is not its whole name.
    page = three(editor)
    tool.click(page, xy(thumb(page, 0)))
    expect(thumb(page, 0)).to_have_attribute("aria-pressed", "true")
    said = tool.ctrl_click(page, xy(thumb(page, 2)))
    assert said.startswith("ctrl-clicked at ")
    expect(thumb(page, 0)).to_have_attribute("aria-pressed", "true")
    expect(thumb(page, 1)).to_have_attribute("aria-pressed", "false")
    expect(thumb(page, 2)).to_have_attribute("aria-pressed", "true")
    expect(menu(page)).to_have_count(0)
    tool.ctrl_click(page, xy(thumb(page, 2)))
    expect(thumb(page, 2)).to_have_attribute("aria-pressed", "false")
    expect(thumb(page, 0)).to_have_attribute("aria-pressed", "true")


def test_finger_held_on_a_block_opens_the_menu_when_it_lifts(editor):
    page = editor(box("a", "text", TEXT))
    said = tool.finger(page, xy(at(page, "a")))
    assert said.startswith("held a finger at ")
    expect(menu(page)).to_be_visible()


def test_finger_held_on_a_thumbnail_opens_the_page_menu(editor):
    page = three(editor)
    said = tool.finger(page, xy(thumb(page, 1)))
    assert said.startswith("held a finger at ")
    expect(menu(page)).to_be_visible()
    expect(menu(page).get_by_role("menuitem", name="Seite löschen")).to_be_visible()


def test_mic_lets_a_recording_stop_when_the_form_shuts(editor):
    page = editor(box("a", "text", TEXT))
    said = tool.mic(page)
    assert "microphone" in said
    tool.click(page, "Feedback")
    expect(page.locator("dialog.feedback")).to_be_visible()
    tool.click(page, "\u25cf Aufnahme starten")
    expect(page.get_by_role("button", name="Aufnahme beenden")).to_be_visible()
    tool.key(page, "Escape")
    expect(page.locator("dialog.feedback")).to_have_count(0)
    page.wait_for_function(
        "window.__tracks && window.__tracks.length === 1 && window.__tracks.every((t) => t.stopped)"
    )
    tool.click(page, "Feedback")
    expect(page.locator("dialog.feedback").get_by_role("status")).to_have_text(KEPT)
    expect(page.locator("dialog.feedback ul.clips li")).to_have_count(1)


def test_paste_word_keeps_bold_italic_and_a_list(editor):
    client = user()
    page = editor(client=client)
    said = tool.paste_word(page, "Ein *fett* und _schief_ Wort\\n- eins\\n1. zwei")
    assert said.startswith('pasted from Word: "Ein fett und schief Wort')
    block = next(b for b in saved(page, client) if b["type"] == "text")
    paras = block["props"]["rich"]

    def run(words):
        return next(r for p in paras for r in p["runs"] if words in r["text"])

    assert run("fett").get("bold") is True
    assert run("schief").get("italic") is True
    assert not run("Ein").get("bold")
    assert [(p.get("list"), p["runs"][0]["text"]) for p in paras[1:]] == [
        ("bullet", "eins"),
        ("number", "zwei"),
    ]
    assert "<script>" not in block["props"]["text"]


def test_paste_word_escapes_a_tag_the_teacher_typed(editor):
    client = user()
    page = editor(client=client)
    tool.paste_word(page, "<script>alert(1)</script>")
    block = next(b for b in saved(page, client) if b["type"] == "text")
    assert "alert" in block["props"]["text"]
    assert block["type"] == "text"


def test_drop_web_of_a_file_lands_the_picture(editor, folder):
    (folder / "bild.png").write_bytes(png())
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    x, y = spot(page, 105, 150)
    said = tool.drop_web(page, "bild.png", f"{x:g},{y:g}")
    assert said.startswith("dropped bild.png as a web picture at ")
    expect(blocks(page)).to_have_count(2)
    assert any(b["type"] == "image" for b in saved(page, client))


def test_drop_web_of_an_address_shows_the_hint_and_fetches_nothing(editor):
    page = editor(box("a", "text", TEXT))
    asked = []
    page.on("request", lambda r: asked.append(r.url))
    x, y = spot(page, 105, 150)
    said = tool.drop_web(page, "https://example.org/katze.png", f"{x:g},{y:g}")
    assert "fetches nothing" in said
    expect(page.locator(".notice.fault")).to_contain_text(WEB_PICTURE)
    expect(blocks(page)).to_have_count(1)
    assert [u for u in asked if "example.org" in u] == []
