import os
import time

from playwright.sync_api import expect
from ui import at, pick, picture, upload, user

from blattwerk import pictures

DRAWN = ".block .picture img"


def saves(response):
    return response.request.method == "PATCH" and "/api/sheets/" in response.url


def test_undo_brings_a_deleted_old_picture_back_and_it_loads(editor, data_dir):
    client = user()
    shown = upload(client)
    file = pictures.path(client.get("/api/me").json()["id"], shown)
    # Uploaded long ago, on a sheet no one has saved since.
    long_ago = time.time() - (pictures.KEEP_DAYS + 1) * 86400
    os.utime(file, (long_ago, long_ago))
    page = editor(picture(shown), client=client)
    expect(page.locator(DRAWN)).to_have_js_property("naturalWidth", 3)

    pick(page, "image")
    with page.expect_response(saves) as saved:
        page.keyboard.press("Delete")
    assert saved.value.ok
    expect(at(page, "image")).to_have_count(0)
    assert file.is_file()

    with page.expect_response(saves) as saved:
        page.keyboard.press("Control+z")
    assert saved.value.ok
    expect(page.locator(DRAWN)).to_have_js_property("naturalWidth", 3)
    # A new page load asks the server for the picture, not the browser's cache.
    page.reload()
    expect(page.locator(DRAWN)).to_have_js_property("naturalWidth", 3)
    assert client.get(f"/api/uploads/{shown}").status_code == 200
