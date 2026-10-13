"""A block of a type the running script does not know, as a newer Blattomat leaves it in a sheet.

It draws a plain line, survives a save untouched, and does not break the editor's keys or panel.
"""

import httpx
from playwright.sync_api import expect
from ui import TEXT, at, box, doc, pick, picked, reload, sheet, user

from blattwerk import pdf

LINE = "Dieser Block braucht eine neuere Version von Blattomat."


def unknown(name="u", z=1):
    return box(name, "zukunft", {"neu": [1, {"x": 2}]}, z=z)


def known():
    return box("t", "text", TEXT, z=2)


def watch(page):
    """Collects the page's errors from now on: uncaught ones and those the console logs."""
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda m: m.type == "error" and errors.append(m.text))
    return errors


def stored(client, page):
    """The blocks of the first page as the server holds them, by name."""
    return {b["id"]: b for b in doc(page, client)["pages"][0]["blocks"]}


def test_the_editor_opens_a_sheet_with_an_unknown_block(editor):
    page = editor(unknown(), known())
    expect(at(page, "u").locator(".unknown")).to_have_text(LINE)


def test_the_thumbnail_draws_the_plain_line(editor, server):
    page = editor(unknown(), known())
    page.goto(server)
    expect(page.locator(".sheets li .paper .unknown")).to_have_text(LINE)


def test_print_draws_the_plain_line_and_is_ready(browser, server):
    client = user()
    mine = sheet(client, [unknown(), known()])["id"]
    context = browser.new_context()
    context.add_cookies([{"name": "session", "value": client.cookies["session"], "url": server}])
    context.add_init_script("localStorage.setItem('tour', '1')")
    page = context.new_page()
    errors = watch(page)
    page.set_extra_http_headers({"X-Render-Token": pdf.new_token(mine)})
    page.goto(f"{server}/druck/{mine}")
    page.wait_for_selector("body.ready", state="attached")
    expect(page.locator(".unknown")).to_have_text(LINE)
    assert not errors, errors
    context.close()


def test_the_pdf_comes(server):
    client = user()
    mine = sheet(client, [unknown(), known()])["id"]
    # The PDF is made by a Chromium that calls this server, so the test asks a running one.
    cookie = {"Cookie": f"session={client.cookies['session']}"}
    response = httpx.get(f"{server}/api/sheets/{mine}/pdf", headers=cookie, timeout=60)
    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")


def test_a_save_leaves_the_unknown_block_as_it_was(editor):
    client = user()
    page = editor(unknown(), known(), client=client)
    pick(page, "t")
    page.keyboard.press("ArrowDown")
    expect(page.locator(".block.sel")).to_have_count(1)
    assert stored(client, page)["u"] == unknown()
    expect(at(page, "u").locator(".unknown")).to_have_text(LINE)
    reload(page, page.url)
    expect(at(page, "u").locator(".unknown")).to_have_text(LINE)
    assert stored(client, page)["u"] == unknown()


def test_the_unknown_block_can_be_picked_moved_deleted_and_brought_back(editor):
    client = user()
    page = editor(unknown(), known(), client=client)
    errors = watch(page)
    pick(page, "u")
    page.keyboard.press("ArrowDown")
    expect(at(page, "u")).to_have_class("block sel")
    page.keyboard.press("Delete")
    expect(at(page, "u")).to_have_count(0)
    page.keyboard.press("Control+z")
    expect(at(page, "u")).to_have_count(1)
    page.keyboard.press("Control+z")
    assert stored(client, page)["u"] == unknown()
    assert not errors, errors


def test_copy_and_paste_keep_type_and_props(editor):
    client = user()
    page = editor(unknown(), known(), client=client)
    errors = watch(page)
    pick(page, "u")
    page.keyboard.press("Control+c")
    page.keyboard.press("Control+v")
    expect(page.locator(".block[data-id]")).to_have_count(3)
    copies = [b for b in doc(page, client)["pages"][0]["blocks"] if b["type"] == "zukunft"]
    assert len(copies) == 2
    assert all(b["props"] == unknown()["props"] for b in copies)
    assert not errors, errors


def test_ctrl_d_duplicates_it_as_it_is(editor):
    client = user()
    page = editor(unknown(), known(), client=client)
    errors = watch(page)
    pick(page, "u")
    page.keyboard.press("Control+d")
    expect(page.locator(".block[data-id]")).to_have_count(3)
    copies = [b for b in doc(page, client)["pages"][0]["blocks"] if b["type"] == "zukunft"]
    assert len(copies) == 2
    assert all(b["props"] == unknown()["props"] for b in copies)
    assert not errors, errors


def test_enter_f2_and_double_click_break_nothing(editor):
    client = user()
    page = editor(unknown(), known(), client=client)
    errors = watch(page)
    pick(page, "u")
    page.keyboard.press("Enter")
    page.keyboard.press("F2")
    at(page, "u").dblclick()
    expect(at(page, "u").locator(".unknown")).to_have_text(LINE)
    expect(page.locator(".block.sel")).to_have_count(1)
    assert not errors, errors


def test_picked_with_a_known_block_the_panel_does_not_break(editor):
    page = editor(unknown(), known())
    errors = watch(page)
    pick(page, "t", "u")
    expect(page.locator(".block.sel")).to_have_count(2)
    assert picked(page) in (["t", "u"], ["u", "t"])
    assert not errors, errors


def test_picked_alone_the_panel_shows_its_place(editor):
    page = editor(unknown(), known())
    errors = watch(page)
    pick(page, "u")
    expect(page.get_by_label("X", exact=True)).to_be_visible()
    expect(page.get_by_label("Y", exact=True)).to_be_visible()
    assert not errors, errors
