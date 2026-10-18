"""Text in a shape lies in the rectangle that fits inside its outline, as PowerPoint sets it."""

import io

import httpx
import pytest
from playwright.sync_api import expect
from pypdf import PdfReader
from ui import FIELD, RECT, at, box, pick, saved, user

# Three lines, as a pupil types them after Enter.
LINES = {
    "rich": [{"runs": [{"text": word}]} for word in ("Eins", "Zwei", "Drei")],
    "size": 14,
    "align": "center",
}
# The side of a square inscribed in a circle, as a share of its diameter.
ROOT = 2**-0.5


def shape(kind, **more):
    """A shape of the kind with its three lines; `more` replaces any of its props."""
    return {**RECT, **LINES, "kind": kind, "inside": True, **more}


def lines(page, name):
    """The box of every line of the block's text, as the browser draws it, in screen px."""
    return (
        at(page, name)
        .locator(".frame")
        .evaluate(
            """el => {
            const out = [];
            for (const p of el.querySelectorAll("p")) {
                const range = document.createRange();
                range.selectNodeContents(p);
                for (const r of range.getClientRects())
                    out.push({ left: r.left, top: r.top, right: r.right, bottom: r.bottom });
            }
            return out;
        }"""
        )
    )


def frame(page, name):
    """The block's box on the screen, as a dict of edges."""
    b = at(page, name).locator(".frame").bounding_box()
    return {
        "left": b["x"],
        "top": b["y"],
        "right": b["x"] + b["width"],
        "bottom": b["y"] + b["height"],
    }


def inside(rects, left, top, right, bottom, tol=1.0):
    """Every rect lies within the edges, to a pixel."""
    assert rects, "no text is drawn"
    for r in rects:
        assert r["left"] >= left - tol, (r, left)
        assert r["right"] <= right + tol, (r, right)
        assert r["top"] >= top - tol, (r, top)
        assert r["bottom"] <= bottom + tol, (r, bottom)


def test_circle_text_lies_in_its_inscribed_square(editor):
    # A long first line is wider than the square: it runs over the outline, unless it stays inside.
    long = shape(
        "circle",
        rich=[
            {"runs": [{"text": "Ein langer Satz steht"}]},
            {"runs": [{"text": "Zwei"}]},
            {"runs": [{"text": "Drei"}]},
        ],
    )
    page = editor(box("a", "shape", long, x=20, y=30, w=60, h=60))
    pick(page, "a")
    box_ = frame(page, "a")
    w, h = box_["right"] - box_["left"], box_["bottom"] - box_["top"]
    # A circle of width w has its inscribed square inset (1 - 1/sqrt2) / 2 of w on each side.
    inset_x, inset_y = w * (1 - ROOT) / 2, h * (1 - ROOT) / 2
    inside(
        lines(page, "a"),
        box_["left"] + inset_x,
        box_["top"] + inset_y,
        box_["right"] - inset_x,
        box_["bottom"] - inset_y,
    )


def test_triangle_text_starts_below_the_middle_of_the_box(editor):
    page = editor(box("a", "shape", shape("triangle"), x=20, y=30, w=60, h=60))
    pick(page, "a")
    b = frame(page, "a")
    middle = (b["top"] + b["bottom"]) / 2
    inside(
        lines(page, "a"),
        b["left"] + (b["right"] - b["left"]) / 4,
        middle,
        b["right"] - (b["right"] - b["left"]) / 4,
        b["bottom"],
    )


def test_flipped_triangle_text_is_in_the_top_half(editor):
    page = editor(box("a", "shape", shape("triangle"), x=20, y=30, w=60, h=60, flipY=True))
    pick(page, "a")
    b = frame(page, "a")
    middle = (b["top"] + b["bottom"]) / 2
    inside(
        lines(page, "a"),
        b["left"] + (b["right"] - b["left"]) / 4,
        b["top"],
        b["right"] - (b["right"] - b["left"]) / 4,
        middle,
    )


def test_star_text_lies_in_the_inner_pentagon_box(editor):
    page = editor(box("a", "shape", shape("star"), x=20, y=30, w=60, h=60))
    pick(page, "a")
    b = frame(page, "a")
    w, h = b["right"] - b["left"], b["bottom"] - b["top"]
    # The star's points alternate outer and inner: the inner ones are the odd ones of its outline.
    points = at(page, "a").locator(".frame svg.outline polygon").get_attribute("points").split()
    xy = [tuple(float(v) for v in p.split(",")) for p in points]
    inner = xy[1::2]
    xs, ys = [x / 60 for x, _ in inner], [y / 60 for _, y in inner]
    inside(
        lines(page, "a"),
        b["left"] + min(xs) * w,
        b["top"] + min(ys) * h,
        b["left"] + max(xs) * w,
        b["top"] + max(ys) * h,
    )


def test_bubble_text_lies_in_the_body_above_the_tail(editor):
    page = editor(box("a", "shape", shape("bubble"), x=20, y=30, w=60, h=60))
    pick(page, "a")
    b = frame(page, "a")
    h = b["bottom"] - b["top"]
    inside(lines(page, "a"), b["left"], b["top"], b["right"], b["top"] + 0.75 * h)


def test_rect_text_keeps_its_whole_width(editor):
    # A long first line fills the box: a rect keeps all of its width, as it did before.
    long = shape(
        "rect",
        rich=[
            {"runs": [{"text": "Ein langer Satz steht"}]},
            {"runs": [{"text": "Zwei"}]},
            {"runs": [{"text": "Drei"}]},
        ],
    )
    page = editor(box("a", "shape", long, x=20, y=30, w=60, h=60))
    pick(page, "a")
    b = frame(page, "a")
    rects = lines(page, "a")
    # The padding of a rect is unchanged: the line reaches out to within a few mm of the edges.
    assert min(r["left"] for r in rects) - b["left"] < 0.15 * (b["right"] - b["left"])
    assert b["right"] - max(r["right"] for r in rects) < 0.15 * (b["right"] - b["left"])


def test_typing_in_a_triangle_stays_in_its_inner_box(editor):
    page = editor(box("a", "shape", shape("triangle", text="", rich=None), x=20, y=30, w=60, h=60))
    pick(page, "a")
    page.keyboard.press("Enter")
    page.keyboard.type("Eins")
    page.keyboard.press("Enter")
    page.keyboard.type("Zwei")
    expect(page.locator(FIELD)).to_contain_text("Zwei")
    b = frame(page, "a")
    w, h = b["right"] - b["left"], b["bottom"] - b["top"]
    field = page.locator(FIELD).bounding_box()
    inside(
        [
            {
                "left": field["x"],
                "top": field["y"],
                "right": field["x"] + field["width"],
                "bottom": field["y"] + field["height"],
            }
        ],
        b["left"] + w / 4,
        b["top"] + h / 2,
        b["right"] - w / 4,
        b["bottom"],
    )


def test_small_circle_keeps_one_word_inside_its_inscribed_square(editor):
    page = editor(
        box(
            "a",
            "shape",
            shape("circle", size=8, rich=[{"runs": [{"text": "Ja"}]}]),
            x=20,
            y=30,
            w=12,
            h=12,
        )
    )
    pick(page, "a")
    b = frame(page, "a")
    w, h = b["right"] - b["left"], b["bottom"] - b["top"]
    inset_x, inset_y = w * (1 - ROOT) / 2, h * (1 - ROOT) / 2
    inside(
        lines(page, "a"),
        b["left"] + inset_x,
        b["top"] + inset_y,
        b["right"] - inset_x,
        b["bottom"] - inset_y,
    )


def test_flipped_star_text_lies_in_its_inner_pentagon_box(editor):
    page = editor(box("a", "shape", shape("star"), x=20, y=30, w=60, h=60, flipY=True))
    pick(page, "a")
    b = frame(page, "a")
    w, h = b["right"] - b["left"], b["bottom"] - b["top"]
    points = at(page, "a").locator(".frame svg.outline polygon").get_attribute("points").split()
    xy = [tuple(float(v) for v in p.split(",")) for p in points]
    inner = xy[1::2]
    xs, ys = [x / 60 for x, _ in inner], [1 - y / 60 for _, y in inner]
    inside(
        lines(page, "a"),
        b["left"] + min(xs) * w,
        b["top"] + min(ys) * h,
        b["left"] + max(xs) * w,
        b["top"] + max(ys) * h,
    )


def test_pdf_triangle_text_lands_in_the_bottom_half(editor, server):
    client = user()
    page = editor(box("a", "shape", shape("triangle"), x=20, y=30, w=60, h=60), client=client)
    cookie = {"Cookie": f"session={client.cookies['session']}"}
    sheet_id = page.url.rsplit("/", 1)[1]
    res = httpx.get(f"{server}/api/sheets/{sheet_id}/pdf", headers=cookie, timeout=60)
    assert res.status_code == 200
    reader = PdfReader(io.BytesIO(res.content))
    first = reader.pages[0]
    top = float(first.mediabox.top)
    spots = []

    def visit(text, cm, tm, font, size):
        if text.strip():
            spots.append((text.strip(), top - (cm[5] + tm[5] * cm[3] + tm[4] * cm[1])))

    first.extract_text(visitor_text=visit)
    mm = {word: y * 25.4 / 72 for word, y in spots}
    # The triangle is 30 mm to 90 mm down the page: its text lies below the middle, from 60 mm.
    words = [mm[w] for w in ("Eins", "Zwei", "Drei") if w in mm]
    assert len(words) == 3, spots
    assert min(words) > 30 + 30, (spots, top, first.mediabox)


# Six words, one to a line: they fill a 40 mm shape at 14 pt from top to bottom.
FULL = {
    "rich": [{"runs": [{"text": w}]} for w in ("Eins", "Zwei", "Drei", "Vier", "Fuenf", "Sechs")],
    "size": 14,
    "align": "center",
}


def printed(page, client, server):
    """Each word of the sheet's PDF and how far down the page it stands, in mm."""
    cookie = {"Cookie": f"session={client.cookies['session']}"}
    sheet_id = page.url.rsplit("/", 1)[1]
    res = httpx.get(f"{server}/api/sheets/{sheet_id}/pdf", headers=cookie, timeout=60)
    assert res.status_code == 200
    first = PdfReader(io.BytesIO(res.content)).pages[0]
    top = float(first.mediabox.top)
    spots = {}

    def visit(text, cm, tm, font, size):
        if text.strip():
            spots[text.strip()] = (top - (cm[5] + tm[5] * cm[3] + tm[4] * cm[1])) * 25.4 / 72

    first.extract_text(visitor_text=visit)
    return spots


@pytest.mark.parametrize("kind", ["circle", "triangle", "star"])
def test_a_saved_shape_full_of_text_prints_all_of_it_where_it_did(editor, server, kind):
    """A shape saved before #128 has no `inside`: its text keeps the whole box, on screen and in
    the PDF, so no line that printed before is lost below the outline."""
    client = user()
    props = {**RECT, **FULL, "kind": kind, "valign": "top"}
    page = editor(box("a", "shape", props, x=20, y=30, w=40, h=40), client=client)
    b = frame(page, "a")
    rects = lines(page, "a")
    assert len({round(r["top"]) for r in rects}) == 6, rects
    # The first line starts at the box's top, not in its middle or lower half.
    assert min(r["top"] for r in rects) < b["top"] + 0.15 * (b["bottom"] - b["top"]), (rects[0], b)
    spots = printed(page, client, server)
    words = ("Eins", "Zwei", "Drei", "Vier", "Fuenf", "Sechs")
    assert all(w in spots for w in words), spots
    # The box is 30 to 70 mm down the page: the first word's foot prints in its top quarter, the
    # last in the box.
    assert spots["Eins"] < 30 + 40 / 4, spots
    assert spots["Sechs"] < 70, spots


@pytest.mark.parametrize("label", ["Kreis", "Dreieck", "Stern"])
def test_a_shape_made_now_keeps_its_text_inside(editor, label):
    """A shape from the insert bar is made with the inside rule: its text starts below the top."""
    client = user()
    page = editor(client=client)
    page.locator(".insert").get_by_label(label, exact=True).click()
    page.keyboard.press("Enter")
    page.keyboard.type("Hallo")
    page.keyboard.press("Escape")
    (a,) = saved(page, client)
    assert a["props"]["inside"] is True


def test_a_text_turned_into_a_triangle_in_the_panel_keeps_its_text_inside(editor):
    client = user()
    page = editor(
        box("a", "text", {**LINES, "text": "Eins"}, x=20, y=30, w=60, h=60), client=client
    )
    pick(page, "a")
    page.locator(".panel").get_by_role("button", name="Dreieck", exact=True).click()
    b = frame(page, "a")
    expect(at(page, "a").locator(".frame svg.outline")).to_have_count(1)
    # Far below the top, where a text with no outline starts.
    assert min(r["top"] for r in lines(page, "a")) >= b["top"] + 0.4 * (b["bottom"] - b["top"])
    (a,) = saved(page, client)
    assert a["props"]["inside"] is True


def same_size(page, name, outline):
    """The outline's box is the block's box, to a pixel or two."""
    b = frame(page, name)
    ob = outline.bounding_box()
    assert abs(ob["x"] - b["left"]) < 2 and abs(ob["y"] - b["top"]) < 2, (ob, b)
    assert abs(ob["width"] - (b["right"] - b["left"])) < 2, (ob, b)
    assert abs(ob["height"] - (b["bottom"] - b["top"])) < 2, (ob, b)


DACH = {"rich": [{"runs": [{"text": "Dach"}]}], "size": 14, "align": "center"}


@pytest.mark.parametrize("valign", ["top", "middle", "bottom"])
@pytest.mark.parametrize("kind", ["circle", "triangle", "star"])
def test_a_fitting_word_keeps_outline_and_size_at_each_valign(editor, kind, valign):
    page = editor(box("a", "shape", shape(kind, **DACH, valign=valign), x=20, y=30, w=60, h=50))
    pick(page, "a")
    fr = at(page, "a").locator(".frame")
    assert fr.get_attribute("data-cut") is None
    assert "100%" not in fr.evaluate("el => getComputedStyle(el).clipPath")
    assert fr.evaluate("el => el.style.getPropertyValue('--fit')") in ("", "1")
    if kind != "circle":
        same_size(page, "a", at(page, "a").locator(".frame svg.outline"))


@pytest.mark.parametrize("kind", ["circle", "triangle", "star"])
def test_pdf_prints_outline_and_word_at_the_bottom(editor, server, kind):
    client = user()
    page = editor(
        box("a", "shape", shape(kind, **DACH, valign="bottom"), x=20, y=30, w=60, h=50),
        client=client,
    )
    spots = printed(page, client, server)
    assert "Dach" in spots, spots
    # The shape is 30 to 80 mm down the page: its word lies in the lower half.
    assert spots["Dach"] > 55, spots


def test_a_text_too_long_is_cut_in_its_room_and_keeps_the_outline(editor):
    page = editor(box("a", "shape", shape("triangle", **FULL), x=20, y=30, w=40, h=40))
    pick(page, "a")
    fr = at(page, "a").locator(".frame")
    assert fr.get_attribute("data-cut") == "true"
    same_size(page, "a", at(page, "a").locator(".frame svg.outline"))
    foot = fr.evaluate(
        "el => el.getBoundingClientRect().bottom - parseFloat(getComputedStyle(el).paddingBottom)"
    )
    # Lines whose box ends past the foot are cut away: the rest end above it.
    ends = [r["bottom"] - (r["bottom"] - r["top"]) / 2 for r in lines(page, "a")]
    assert ends and min(ends) < foot, (ends, foot)


@pytest.mark.parametrize("valign", ["top", "middle", "bottom"])
def test_a_bubble_keeps_outline_at_each_valign(editor, valign):
    page = editor(box("a", "shape", shape("bubble", **DACH, valign=valign), x=20, y=30, w=60, h=50))
    expect(at(page, "a").locator(".frame svg.outline")).to_be_visible()
    assert at(page, "a").locator(".frame").get_attribute("data-cut") is None
