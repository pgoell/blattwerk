"""A picture file dropped on the desk uploads and lands where it was dropped."""

import base64
import re

import pytest
from playwright.sync_api import expect
from test_clipboard import REFUSED, blocks, button, every, stored
from ui import FIELD, RECT, TABLE, TEXT, at, box, centre, drop, pick, png, saved, user

PNG = ("bild.png", "image/png", png())
PDF = ("blatt.pdf", "application/pdf", b"%PDF-1.4\n")
# One pixel, the smallest GIF a browser draws.
GIF = base64.b64decode("R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7")
KEPT = {"dragover": True, "drop": True}
KINDS = ["text", "rect", "line", "picture", "table", "ruling", "maths", "symbol"]
# The canvas gives the browser's own JPEG or WebP of three by two red pixels.
DRAWN = """(type) => {
    const canvas = document.createElement("canvas");
    [canvas.width, canvas.height] = [3, 2];
    const pen = canvas.getContext("2d");
    pen.fillStyle = "red";
    pen.fillRect(0, 0, 3, 2);
    return canvas.toDataURL(type);
}"""


def shot(page, kind):
    """A picture file of the kind, and how many pixels wide and high it is."""
    if kind == "png":
        return (*PNG, 3, 2)
    if kind == "gif":
        return ("bild.gif", "image/gif", GIF, 1, 1)
    head, data = page.evaluate(DRAWN, f"image/{kind}").split(",")
    # A browser that cannot write the kind writes a PNG in its place.
    assert head == f"data:image/{kind};base64"
    return (f"bild.{kind}", f"image/{kind}", base64.b64decode(data), 3, 2)


def spot(page, x, y, n=0):
    """The point of the window that lies x and y mm into page n, an A4 page."""
    held = page.locator(f'.sheet[data-page="{n}"]').bounding_box()
    k = held["width"] / 210
    return held["x"] + x * k, held["y"] + y * k


def beside(page, n=0):
    """A point of the desk left of page n, half way down it: no page lies under the pointer."""
    held = page.locator(f'.sheet[data-page="{n}"]').bounding_box()
    point = held["x"] - 12, held["y"] + held["height"] / 2
    assert page.evaluate("([x, y]) => document.elementFromPoint(x, y).className", point) == "desk"
    return point


def landed(page, count, pictures=1, width=3):
    """Waits for `count` blocks with the dropped pictures alone selected and drawn. Gives those."""
    expect(blocks(page)).to_have_count(count)
    expect(page.locator(".block.sel")).to_have_count(pictures)
    drawn = page.locator(".block.sel .picture img")
    expect(drawn).to_have_count(pictures)
    for i in range(pictures):
        expect(drawn.nth(i)).to_have_attribute("src", re.compile(r"/api/uploads/\d+$"))
        # A picture that failed to load has no width.
        expect(drawn.nth(i)).to_have_js_property("naturalWidth", width)
    return page.locator(".block.sel")


def docs(page, client):
    """Every page's blocks as the server holds them, once the editor has saved a change."""
    saved(page, client)
    pages = client.get(f"/api/sheets/{page.url.rsplit('/', 1)[1]}").json()["doc"]["pages"]
    return [p["blocks"] for p in pages]


def new(found, *old):
    """The blocks that were not there before, from back to front."""
    return sorted((b for b in found if b["id"] not in old), key=lambda b: b["z"])


def middle(b):
    return b["x"] + b["w"] / 2, b["y"] + b["h"] / 2


@pytest.mark.parametrize("kind", ["png", "jpeg", "webp", "gif"])
def test_a_dropped_picture_file_becomes_a_picture_block(editor, kind):
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    *file, width, height = shot(page, kind)
    drop(page, *spot(page, 105, 150), tuple(file))
    src = landed(page, 2, width=width).locator("img").get_attribute("src")
    [held] = new(saved(page, client), "a")
    assert held["type"] == "image"
    assert held["props"] == {
        "upload": int(src.rsplit("/", 1)[1]),
        "ratio": pytest.approx(width / height),
        "cut": [0, 0, 0, 0],
    }
    # As the button Bild sizes it: 100 mm wide, and no higher than that.
    assert (held["w"], held["h"]) == (100, round(100 * height / width, 2))


def test_the_picture_lands_with_its_middle_under_the_pointer(editor):
    page = editor(box("a", "text", TEXT))
    point = spot(page, 120, 90)
    drop(page, *point, PNG)
    assert centre(landed(page, 2)) == pytest.approx(point, abs=1)


def test_a_drop_lands_under_the_pointer_when_zoomed(editor):
    page = editor(box("a", "text", TEXT))
    wide = page.locator(".sheet").evaluate("el => el.offsetWidth")
    page.get_by_label("Größer", exact=True).click()
    expect(page.locator(".sheet")).not_to_have_js_property("offsetWidth", wide)
    # The page is now wider than the desk, and the desk's middle is well inside the page.
    point = centre(page.locator(".desk"))
    drop(page, *point, PNG)
    assert centre(landed(page, 2)) == pytest.approx(point, abs=1)


def test_the_browser_keeps_no_drop_for_itself(editor):
    """A file the page lets go is one the browser opens in place of the editor."""
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    url = page.url
    # Off the desk first: a block one of these added would be there by the end.
    for off in ("header", "aside.panel"):
        assert drop(page, *centre(page.locator(off)), PNG) == KEPT
    assert drop(page, *beside(page), PNG) == KEPT
    landed(page, 2)
    assert drop(page, *spot(page, 105, 150), PNG) == KEPT
    landed(page, 3)
    assert len(new(saved(page, client), "a")) == 2
    assert page.url == url


def test_the_dropped_picture_is_the_selection(editor):
    page = editor(box("a", "text", TEXT), box("b", "shape", RECT, z=2))
    pick(page, "a")
    drop(page, *spot(page, 105, 150), PNG)
    landed(page, 3)
    expect(at(page, "a")).to_have_class("block")


def test_undo_takes_a_dropped_picture_away_and_redo_brings_it_back(editor):
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    drop(page, *spot(page, 105, 150), PNG)
    landed(page, 2)
    page.keyboard.press("Control+z")
    expect(blocks(page)).to_have_count(1)
    expect(at(page, "a")).to_be_visible()
    page.keyboard.press("Control+y")
    expect(blocks(page)).to_have_count(2)
    expect(page.locator(".picture img")).to_have_js_property("naturalWidth", 3)
    assert [b["type"] for b in new(saved(page, client), "a")] == ["image"]


@pytest.mark.parametrize("where", ["corner", "desk", "other"])
def test_a_drop_beside_the_page_lands_whole_on_it(editor, where):
    """Beside a page that is not the one in use, "other", the picture goes to that page."""
    client = user()
    n = int(where == "other")
    page = editor(box("a", "text", TEXT), more=[box("far", "text", TEXT)] * n, client=client)
    before = stored(page, client)
    sheet = page.locator(f'.sheet[data-page="{n}"]')
    sheet.scroll_into_view_if_needed()
    held = sheet.bounding_box()
    point = spot(page, 208, 2) if where == "corner" else beside(page, n)
    drop(page, *point, PNG)
    got = landed(page, 2 + n).bounding_box()
    expect(sheet.locator(".block.sel")).to_have_count(1)
    if n:
        assert docs(page, client)[0] == before
    right, top = got["x"] + got["width"], got["y"]
    if where == "corner":
        # The upper right corner: the block touches both of its edges.
        assert (right, top) == pytest.approx((held["x"] + held["width"], held["y"]), abs=1)
    else:
        # Moved across onto the page, and no further down or up than the pointer.
        assert (got["x"], top + got["height"] / 2) == pytest.approx((held["x"], point[1]), abs=1)
    assert got["x"] >= held["x"] - 1
    assert right <= held["x"] + held["width"] + 1
    assert held["y"] - 1 <= top
    assert top + got["height"] <= held["y"] + held["height"] + 1


@pytest.mark.parametrize("kind", ["text", "table"])
def test_a_drop_while_typing_keeps_the_text(editor, kind):
    """A file manager sends the file's address along as text, which an open field would take."""
    client = user()
    page = editor(box("a", kind, TEXT if kind == "text" else TABLE), client=client)
    pick(page, "a")
    # Enter opens the text, or the first cell, with all of it picked.
    page.keyboard.press("Enter")
    field = page.locator(FIELD if kind == "text" else ".block textarea:focus")
    page.keyboard.type("du")
    (expect(field).to_have_text if kind == "text" else expect(field).to_have_value)("du")
    drop(page, *centre(field), PNG, text="file:///home/x/bild.png")
    landed(page, 2)
    expect(page.locator(".desk")).not_to_contain_text("file:")
    [held] = [b for b in saved(page, client) if b["id"] == "a"]
    # A cell's words lie in its field while it is open, so the saved block speaks for both.
    assert "file:" not in str(held)
    if kind == "text":
        expect(at(page, "a")).to_have_text("du")
        assert held["props"]["text"] == "du"
    else:
        assert held["props"]["cells"] == [["du", "Z"], ["3", "7"]]


def test_a_file_that_is_no_picture_is_refused(editor):
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    url = page.url
    # An alert holds the page up until it is answered, so the page notes what it would have said.
    page.evaluate("() => { window.said = []; window.alert = (words) => said.push(words); }")
    drop(page, *spot(page, 105, 150), PDF)
    page.wait_for_function("said.length === 1")
    assert page.evaluate("said[0]").startswith(REFUSED)
    expect(blocks(page)).to_have_count(1)
    assert page.url == url
    drop(page, *spot(page, 105, 150), PDF, PNG)
    landed(page, 2)
    assert [b["type"] for b in new(saved(page, client), "a")] == ["image"]
    # One for each drop, however many of its files are refused.
    assert page.evaluate("said.length") == 2
    assert page.url == url


def test_a_drop_on_the_second_page_lands_there(editor):
    client = user()
    page = editor(box("a", "text", TEXT), more=[box("far", "text", TEXT)], client=client)
    second = page.locator('.sheet[data-page="1"]')
    second.scroll_into_view_if_needed()
    expect(second).to_be_in_viewport()
    drop(page, *spot(page, 105, 148.5, n=1), PNG)
    landed(page, 3)
    expect(second.locator(".block.sel")).to_have_count(1)
    expect(second).to_have_class(re.compile(r"\bon\b"))
    first, other = docs(page, client)
    assert [b["id"] for b in first] == ["a"]
    [held] = new(other, "far")
    assert held["type"] == "image"
    assert middle(held) == pytest.approx((105, 148.5), abs=0.5)


def test_several_files_in_one_drop(editor):
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    files = [(f"{n}.png", "image/png", png(bytes([n, 0, 0]))) for n in range(3)]
    drop(page, *spot(page, 105, 150), *files)
    landed(page, 4, pictures=3)
    held = new(saved(page, client), "a")
    assert [b["type"] for b in held] == ["image"] * 3
    assert len({(b["x"], b["y"]) for b in held}) == 3
    # The first lies at the back, under the pointer; the others step away from it.
    assert middle(held[0]) == pytest.approx((105, 150), abs=0.5)
    page.keyboard.press("Control+z")
    expect(blocks(page)).to_have_count(1)
    expect(at(page, "a")).to_be_visible()


def test_several_files_near_an_edge_stay_clear_of_each_other(editor):
    """At a corner there is no room to step right and down, and none may hide the others."""
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    drop(page, *spot(page, 208, 2), PNG, PNG, PNG)
    landed(page, 4, pictures=3)
    held = new(saved(page, client), "a")
    assert len({(b["x"], b["y"]) for b in held}) == 3
    for b in held:
        assert 0 <= b["x"] <= 210 - b["w"]
        assert 0 <= b["y"] <= 297 - b["h"]


@pytest.mark.parametrize(
    ("own", "press", "pages"),
    [
        (False, "Seite löschen", [["bild", "far"]]),
        (True, "Seite löschen", [["a", "bild"]]),
        (False, "Neue Seite", [["a"], [], ["bild", "far"]]),
    ],
    ids=["another page goes", "its own page goes", "a page comes"],
)
def test_a_page_deleted_or_added_while_the_picture_uploads(editor, own, press, pages):
    """The picture lands on the page it was dropped on, wherever that is by then.

    With that page gone it lands on the page in use. `own` drops on the page in use.
    """
    client = user()
    page = editor(box("a", "text", TEXT), more=[box("far", "text", TEXT)], client=client)
    page.evaluate("() => { window.said = []; window.alert = (words) => said.push(words); }")
    # The server's answer waits until the pages have changed.
    waiting = []
    page.route("**/api/uploads", lambda route: waiting.append(route))
    first, second = (page.locator(f'.sheet[data-page="{n}"]') for n in range(2))
    if own:
        second.click(position={"x": 5, "y": 5})
    second.scroll_into_view_if_needed()
    expect(second if own else first).to_have_class(re.compile(r"\bon\b"))
    with page.expect_request("**/api/uploads"):
        drop(page, *spot(page, 105, 148.5, n=1), PNG)
    button(page, press).click()
    expect(page.locator(".sheet")).to_have_count(len(pages))
    [route] = waiting
    route.continue_()
    expect(blocks(page)).to_have_count(sum(len(p) for p in pages))
    expect(page.locator(".block .picture img")).to_have_js_property("naturalWidth", 3)
    held = docs(page, client)
    assert [sorted("bild" if b["type"] == "image" else b["id"] for b in p) for p in held] == pages
    assert page.evaluate("said") == []


@pytest.mark.parametrize("n", range(11), ids=[*KINDS, "group text", "group rect", "locked"])
def test_a_drop_over_every_block_type_lands_on_top(editor, n):
    client = user()
    # Lower than `every` lays them: a picture over its top row would be moved down onto the page.
    under = [{**b, "y": b["y"] + 15} for b in every(client)]
    under.append(box("lock", "shape", RECT, z=11, x=15, y=185, w=80, locked=True))
    page = editor(*under, client=client)
    before = stored(page, client)
    at(page, under[n]["id"]).scroll_into_view_if_needed()
    # A drag event tells the page whole pixels only.
    point = tuple(int(c) for c in centre(at(page, under[n]["id"])))
    drop(page, *point, PNG)
    # In the middle of the block, not stepped aside as a paste on a taken spot is.
    assert centre(landed(page, 12)) == pytest.approx(point, abs=1)
    held = saved(page, client)
    [top] = new(held, *(b["id"] for b in before))
    assert top["type"] == "image"
    assert top["z"] > max(b["z"] for b in before)
    assert [b for b in held if b["id"] != top["id"]] == before


# What the pointer shows over the point: the page's answer to dragover. A drag made by a script
# keeps no effect it is given, so the answer is noted as the page sets it.
EFFECT = """([x, y]) => {
    const dataTransfer = new DataTransfer();
    dataTransfer.items.add(new File([], "bild.png", { type: "image/png" }));
    let set = "unset";
    Object.defineProperty(dataTransfer, "dropEffect", { set: (effect) => (set = effect) });
    const init = { dataTransfer, clientX: x, clientY: y, bubbles: true, cancelable: true };
    document.elementFromPoint(x, y).dispatchEvent(new DragEvent("dragover", init));
    return set;
}"""


def behind(page):
    """Opens the feedback dialog. Gives a point of the page beside it, under its backdrop."""
    point = spot(page, 10, 10)
    page.get_by_label("Feedback").click()
    expect(page.locator("dialog.feedback")).to_be_visible()
    under = page.evaluate("([x, y]) => document.elementFromPoint(x, y).className", point)
    assert under == "feedback"
    return point


def test_a_drop_while_a_dialog_is_open_adds_nothing(editor):
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    point = behind(page)
    drop(page, *point, PNG)
    page.keyboard.press("Escape")
    expect(page.locator("dialog")).to_have_count(0)
    # A picture of the first drop would be there by the time the second one's is.
    drop(page, *point, PNG)
    landed(page, 2)
    assert [b["type"] for b in new(saved(page, client), "a")] == ["image"]


def test_a_dialog_shows_that_it_takes_no_drop_and_the_browser_keeps_none(editor):
    page = editor(box("a", "text", TEXT))
    url = page.url
    point = behind(page)
    assert page.evaluate(EFFECT, point) == "none"
    assert drop(page, *point, PNG) == KEPT
    page.keyboard.press("Escape")
    expect(page.locator("dialog")).to_have_count(0)
    assert page.evaluate(EFFECT, point) == "copy"
    assert drop(page, *point, PNG) == KEPT
    landed(page, 2)
    assert page.url == url
