"""The teacher-page tool pastes, drops and uploads, and pdf waits out a clash."""
# The fixtures imported below are named again as a test's arguments.
# ruff: noqa: F811

import base64
import re
import time
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

import pytest
from PIL import Image
from playwright.sync_api import expect
from test_teacher_page import (
    ONE,
    folder,  # noqa: F401
    pytestmark,  # noqa: F401
    run,
    tool,
    xy,
)
from ui import (
    PASSWORD,
    box,
    copy_picture,
    copy_text,
    png,
    unpick,
    user,
)


@pytest.mark.native
def test_einfuegen_pastes_what_ctrl_c_copied_in_the_window(folder, server):
    # Issue #430: the bar's Einfügen read the clipboard, and the window never answered its question.
    email = f"{uuid4().hex}@example.com"
    client = user(email)

    def ok(*words):
        done = run(folder, server, *words)
        assert done.returncode == 0, (words, done.stdout, done.stderr)
        return done.stdout

    try:
        ok("start")
        ok("click", "E-Mail")
        ok("type", email)
        ok("click", "Passwort")
        ok("type", PASSWORD)
        ok("key", "Enter")
        said = ok("click", "Neues Blatt")
        found = re.search(r"The page is /blatt/(\w+)", said)
        assert found, said
        sheet_id = found.group(1)
        ok("click", "Beenden")
        ok("click", "Text")
        ok("type", "Hallo")
        ok("key", "Escape")
        ok("key", "Control+c")
        ok("click", "Einfügen")

        def blocks():
            return client.get(f"/api/sheets/{sheet_id}").json()["doc"]["pages"][0]["blocks"]

        late = time.monotonic() + 10
        while len(blocks()) < 2 and time.monotonic() < late:
            time.sleep(0.1)
        assert len(blocks()) == 2
    finally:
        run(folder, server, "stop")


def test_drop_puts_a_picture_on_the_sheet_where_it_lands_and_undo_takes_it_off(editor, folder):
    Image.new("RGB", (40, 30), "red").save(folder / "bild.png")
    page = editor(box("a", "text", ONE))
    tool.drop(page, "bild.png", xy(page.locator(".sheet").first))
    expect(page.locator(".block .picture img")).to_have_count(1)
    tool.key(page, "Control+z")
    expect(page.locator(".block .picture img")).to_have_count(0)


def test_drop_refuses_a_file_outside_the_run_folder_and_one_that_is_missing(
    editor, folder, tmp_path
):
    Image.new("RGB", (40, 30), "red").save(tmp_path / "aussen.png")
    page = editor(box("a", "text", ONE))
    with pytest.raises(tool.Refused, match="outside the run folder"):
        tool.drop(page, "../aussen.png", "100,100")
    with pytest.raises(tool.Refused, match="there is no file"):
        tool.drop(page, "fehlt.png", "100,100")


def test_upload_puts_a_picture_on_the_sheet_by_the_bild_buttons_file_box(editor, folder):
    Image.new("RGB", (40, 30), "red").save(folder / "bild.png")
    page = editor(box("a", "text", ONE))
    tool.upload(page, "bild.png", "Bild")
    expect(page.locator(".block .picture img")).to_have_count(1)


def test_upload_refuses_a_file_outside_the_run_folder_a_missing_one_and_a_target_without_a_file_box(
    editor, folder, tmp_path
):
    Image.new("RGB", (40, 30), "red").save(tmp_path / "aussen.png")
    page = editor(box("a", "text", ONE))
    with pytest.raises(tool.Refused, match="outside the run folder"):
        tool.upload(page, "../aussen.png", "Bild")
    with pytest.raises(tool.Refused, match="there is no file"):
        tool.upload(page, "fehlt.png", "Bild")
    Image.new("RGB", (40, 30), "red").save(folder / "bild.png")
    with pytest.raises(tool.Refused, match="opened no file box"):
        tool.upload(page, "bild.png", "Eins")


def test_paste_elsewhere_takes_the_words_copied_elsewhere(editor):
    page = editor(box("a", "text", ONE))
    copy_text(page, "Eins")
    assert tool.paste_elsewhere(page) == 'another app\'s field took the words "Eins"'
    # The app's page is the one it was.
    assert page.context.pages[0] is page
    expect(page.locator(".block")).to_have_count(1)


def test_paste_elsewhere_says_nothing_when_the_clipboard_is_empty(editor):
    page = editor(box("a", "text", ONE))
    copy_text(page, "")
    assert tool.paste_elsewhere(page) == (
        "another app's field took nothing: the clipboard is empty"
    )


def test_paste_elsewhere_takes_a_picture_copied_in_the_window(editor):
    page = editor(box("a", "text", ONE))
    copy_picture(page)
    said = tool.paste_elsewhere(page)
    assert re.fullmatch(r"another app's field took a picture of \d+ x \d+ px", said), said


def test_paste_elsewhere_takes_the_words_and_the_picture_of_one_copy(editor):
    page = editor(box("a", "text", ONE))
    unpick(page)
    # One copy with a picture and words: the words must survive the picture's wait.
    page.evaluate(
        """async (b64) => {
            const bytes = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
            const picture = new Blob([bytes], { type: "image/png" });
            const words = new Blob(["Hallo"], { type: "text/plain" });
            await navigator.clipboard.write([
                new ClipboardItem({ "image/png": picture, "text/plain": words }),
            ]);
        }""",
        base64.b64encode(png()).decode(),
    )
    said = tool.paste_elsewhere(page)
    assert re.fullmatch(
        r"another app's field took the words \"Hallo\" and a picture of \d+ x \d+ px", said
    ), said


def test_paste_elsewhere_says_only_the_types_when_the_clipboard_holds_html_alone(editor):
    page = editor(box("a", "text", ONE))
    unpick(page)
    page.evaluate(
        """async () => {
            const html = new Blob(["<b>Hallo</b>"], { type: "text/html" });
            await navigator.clipboard.write([new ClipboardItem({ "text/html": html })]);
        }"""
    )
    assert tool.paste_elsewhere(page) == "another app's field took only text/html"


def test_pdf_in_a_clash_says_it_waits_and_the_choice_saves_the_file(editor, folder):
    client = user()
    page = editor(box("a", "text", ONE), client=client)
    sid = urlsplit(page.url).path.rsplit("/", 1)[1]
    # Another device saves the text first, so this page's save is refused.
    theirs = client.get(f"/api/sheets/{sid}").json()
    theirs["doc"]["pages"][0]["blocks"][0]["props"]["text"] = "Vom Tool"
    body = {"doc": theirs["doc"], "version": theirs["version"]}
    assert client.patch(f"/api/sheets/{sid}", json=body).status_code == 200
    tool.click(page, "Eins")
    tool.key(page, "Enter")
    tool.type_(page, "Mein")
    expect(page.locator(".clash")).to_be_visible()
    with pytest.raises(tool.Refused, match="waits for a choice"):
        tool.pdf(page)
    # Once the bar waits, another PDF, or a target that is no button of the bar, is refused at once.
    started = time.monotonic()
    with pytest.raises(tool.Refused, match="waits for a choice"):
        tool.pdf(page)
    with pytest.raises(tool.Refused, match="waits for a choice"):
        tool.pdf(page, "Lösungen")
    assert time.monotonic() - started < 10
    path = Path(tool.pdf(page, "Mit dieser überschreiben"))
    assert path.parent == folder and path.read_bytes().startswith(b"%PDF")
