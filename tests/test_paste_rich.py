"""#234: words pasted from another app keep bold, italic, underline, colour and lists.
What the editor cannot hold drops, and nothing from the web is fetched."""

from playwright.sync_api import expect
from ui import box, pick, saved, unpick, user

# A paste of words from another app: the plain words and the HTML the copy carries.
PASTE = """([html, text]) => {
    const data = new DataTransfer();
    data.setData("text/plain", text);
    data.setData("text/html", html);
    const init = { clipboardData: data, bubbles: true, cancelable: true };
    document.body.dispatchEvent(new ClipboardEvent("paste", init));
}"""
# Into an open text: the paste goes to the field that has the focus.
PASTE_FIELD = """([html, text]) => {
    const data = new DataTransfer();
    data.setData("text/plain", text);
    data.setData("text/html", html);
    const init = { clipboardData: data, bubbles: true, cancelable: true };
    document.activeElement.dispatchEvent(new ClipboardEvent("paste", init));
}"""
TRACKER = (
    '<meta charset="utf-8"><script>alert("nope")</script>'
    '<p>Gruß <a href="http://tracker.invalid/x">Link</a></p>'
    '<img src="http://tracker.invalid/t.png">'
)


def paste(page, html, text):
    unpick(page)
    page.evaluate(PASTE, [html, text])


def pasted(page, client, words):
    """The text block the paste made, as the server holds it."""
    found = saved(page, client)
    return next(b for b in found if b["type"] == "text" and words in b["props"].get("text", ""))


def runs(block):
    """Every run of the block: the rich paragraphs, or the plain text as one run."""
    paras = block["props"].get("rich") or [{"runs": [{"text": block["props"]["text"]}]}]
    return [r for p in paras for r in p["runs"]]


def run(block, words):
    return next(r for r in runs(block) if words in r["text"])


def test_bold_from_a_b_tag_stays_bold(editor):
    """A bold word pasted from a browser is bold on the sheet; its neighbours are not."""
    client = user()
    page = editor(client=client)
    paste(page, "<p>Ein <b>fett</b> Wort</p>", "Ein fett Wort")
    block = pasted(page, client, "fett")
    assert run(block, "fett").get("bold") is True
    assert not run(block, "Ein").get("bold")


def test_bold_from_a_span_with_font_weight_700(editor):
    client = user()
    page = editor(client=client)
    paste(page, '<span style="font-weight:700">dick</span>', "dick")
    assert run(pasted(page, client, "dick"), "dick").get("bold") is True


def test_google_docs_wrapper_is_not_bold(editor):
    """Google Docs wraps all it copies in a bold tag that says normal: the words stay plain."""
    client = user()
    page = editor(client=client)
    html = (
        '<b style="font-weight:normal;" id="docs-internal-guid-1">'
        '<span style="font-weight:400">schlicht</span></b>'
    )
    paste(page, html, "schlicht")
    assert not run(pasted(page, client, "schlicht"), "schlicht").get("bold")


def test_italic_and_underline_stay(editor):
    client = user()
    page = editor(client=client)
    paste(page, "<p><i>schief</i> und <u>unter</u></p>", "schief und unter")
    block = pasted(page, client, "schief")
    assert run(block, "schief").get("italic") is True
    assert run(block, "unter").get("underline") is True


def test_colour_is_kept_as_hex(editor):
    client = user()
    page = editor(client=client)
    paste(page, '<span style="color: rgb(255, 0, 0)">rot</span>', "rot")
    assert run(pasted(page, client, "rot"), "rot").get("color") == "#ff0000"


def test_black_is_dropped_so_the_block_colour_applies(editor):
    client = user()
    page = editor(client=client)
    paste(page, '<span style="color: #000000">schwarz</span>', "schwarz")
    assert "color" not in run(pasted(page, client, "schwarz"), "schwarz")


def test_lists_stay_list_items(editor):
    client = user()
    page = editor(client=client)
    html = "<ul><li>eins</li></ul><ol><li>zwei</li></ol>"
    paste(page, html, "eins\nzwei")
    paras = pasted(page, client, "eins")["props"]["rich"]
    got = [(p["list"], p["runs"][0]["text"]) for p in paras]
    assert got == [("bullet", "eins"), ("number", "zwei")]


def test_script_image_and_link_drop_and_nothing_loads(editor):
    """A script runs nowhere, a tracker's picture or link loads nothing; the link's words stay."""
    client = user()
    page = editor(client=client)
    asked = []
    page.on("request", lambda r: asked.append(r.url))
    paste(page, TRACKER, "Gruß Link")
    block = pasted(page, client, "Link")
    assert "alert" not in block["props"]["text"]
    assert all(b["type"] == "text" for b in saved(page, client))
    page.wait_for_timeout(500)
    assert not [u for u in asked if "tracker.invalid" in u]


def test_one_undo_takes_the_pasted_text_away(editor):
    client = user()
    page = editor(client=client)
    paste(page, "<p><b>weg</b> damit</p>", "weg damit")
    pasted(page, client, "weg")
    page.keyboard.press("Control+z")
    page.wait_for_timeout(1500)
    assert not [b for b in saved(page, client) if "weg" in b["props"].get("text", "")]


def test_a_paste_into_an_open_text_keeps_bold_colour_and_drops_the_script(editor):
    client = user()
    text = {"text": "Hallo", "size": 14, "align": "left"}
    page = editor(box("a", "text", text), client=client)
    pick(page, "a")
    page.keyboard.press("F2")
    expect(page.locator(".ProseMirror")).to_be_focused()
    page.keyboard.press("Control+a")
    html = '<script>alert(1)</script><p><b style="color: rgb(255,0,0)">fett rot</b></p>'
    page.evaluate(PASTE_FIELD, [html, "fett rot"])
    page.keyboard.press("Escape")
    block = next(b for b in saved(page, client) if b["id"] == "a")
    assert "alert" not in block["props"]["text"]
    assert run(block, "fett").get("bold") is True
    assert run(block, "fett").get("color") == "#ff0000"


def test_a_copy_within_the_field_keeps_the_gap_and_not_bold(editor):
    """A gap and a word that is not bold keep both when copied and pasted within the open text."""
    client = user()
    runs_of = [{"text": "Der "}, {"text": "Hund", "gap": True}, {"text": " nicht", "bold": False}]
    rich = [{"runs": runs_of}]
    text = {"text": "Der Hund nicht", "size": 14, "align": "left", "rich": rich}
    page = editor(box("a", "text", text), client=client)
    pick(page, "a")
    page.keyboard.press("F2")
    expect(page.locator(".ProseMirror")).to_be_focused()
    page.keyboard.press("Control+a")
    page.keyboard.press("Control+c")
    page.keyboard.press("End")
    page.keyboard.press("Control+v")
    found = next(b for b in saved(page, client) if b["id"] == "a")
    got = runs(found)
    # Once from the first copy, once from the paste: each of the two keeps its mark.
    assert sum(1 for r in got if r["text"] == "Hund" and r.get("gap")) == 2
    assert sum(1 for r in got if r["text"] == " nicht" and r.get("bold") is False) == 2


# Extra cases a teacher hits. A Word copy carries empty Office paragraphs and no-break spaces, which
# must not add blank lines. A line break in a copy makes two paragraphs.
def test_word_copy_has_no_blank_lines_from_office_paragraphs(editor):
    client = user()
    page = editor(client=client)
    html = (
        '<p class="MsoNormal"><b>Aufgabe</b><o:p></o:p></p>'
        '<p class="MsoNormal"><o:p>&nbsp;</o:p></p><p>Lösung</p>'
    )
    paste(page, html, "Aufgabe\n\nLösung")
    paras = pasted(page, client, "Aufgabe")["props"]["rich"]
    assert [p["runs"][0]["text"] for p in paras] == ["Aufgabe", "Lösung"]


def test_table_cells_from_a_web_page_are_paragraphs_of_their_own(editor):
    client = user()
    page = editor(client=client)
    paste(page, "<table><tr><td>eins</td><td>zwei</td></tr></table>", "eins\tzwei")
    assert pasted(page, client, "eins")["props"]["text"] == "eins\nzwei"


def test_a_line_break_makes_two_lines(editor):
    client = user()
    page = editor(client=client)
    paste(page, "<p>oben<br>unten</p>", "oben\nunten")
    assert pasted(page, client, "oben")["props"]["text"] == "oben\nunten"
