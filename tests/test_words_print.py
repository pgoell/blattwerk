"""A Lineatur takes the sheet's Lernwörter: a word to a row, in copy, trace or row mode (#66)."""

from io import BytesIO

import pytest
from PIL import Image
from playwright.sync_api import expect
from ui import at, box, pick

WORDS = ["Hund", "Katze", "Maus"]
GREY = "rgb(170, 170, 170)"
LONG = "Donaudampfschifffahrtsgesellschaftskapitänsmütze"
MODES = ["copy", "trace", "row"]
FONTS = ["andika", "grund", "va", "sas", "la"]
LINED = ["l1", "l2", "l3", "l4", "lines"]
# A row of each Lineatur in mm, as RULINGS has it.
ROW = {"l1": 20, "l2": 16, "l3": 11.5, "l4": 10, "lines": 8}

# The text of each Karo square of a block, row by row: the squares share a row where their y is one.
SQUARES = """(block) => {
    const rows = new Map();
    for (const text of block.querySelectorAll("svg.ruling text")) {
        const y = text.getAttribute("y");
        rows.set(y, (rows.get(y) ?? "") + text.textContent);
    }
    return [...rows.values()];
}"""


def linked(name, kind, mode, **more):
    return box(name, "ruling", {"kind": kind, "color": "#222222", "list": mode}, **more)


@pytest.mark.parametrize("mode", MODES)
def test_a_linked_block_shows_a_word_to_a_row(editor, mode):
    page = editor(linked("a", "l4", mode, h=40), words=WORDS)
    rows = at(page, "a").locator(".written.listed .row")
    expect(rows).to_have_count(3)
    for i, word in enumerate(WORDS):
        expect(rows.nth(i).locator("span").first).to_have_text(word)
    if mode != "row":
        for i in range(3):
            expect(rows.nth(i).locator("span")).to_have_count(1)
        return
    # The copies that fit the block's width show; the ones past its right edge are cut.
    block = at(page, "a").bounding_box()
    first = rows.nth(0)
    row = first.bounding_box()
    spans = first.locator("span")
    expect(spans.first).to_have_text("Hund")
    inside = [
        s
        for s in (spans.nth(i) for i in range(spans.count()))
        if (box_ := s.bounding_box())
        and box_["x"] >= block["x"]
        and box_["x"] + box_["width"] <= block["x"] + block["width"]
        and box_["x"] + box_["width"] <= row["x"] + row["width"] + 1
        and box_["y"] >= row["y"] - 1
        and box_["y"] + box_["height"] <= row["y"] + row["height"] + 1
    ]
    assert len(inside) >= 2, [s.bounding_box() for s in inside]
    for s in inside:
        expect(s).to_have_text("Hund")


def test_trace_and_row_are_grey_and_copy_is_not(editor):
    for mode in MODES:
        page = editor(linked("a", "l4", mode, h=40), words=WORDS)
        colour = (
            at(page, "a").locator(".written.listed").evaluate("el => getComputedStyle(el).color")
        )
        if mode == "copy":
            assert colour != GREY, mode
        else:
            assert colour == GREY, mode


def test_only_the_rows_of_the_block_are_drawn(editor):
    page = editor(linked("a", "l4", "copy", h=20), words=["eins", "zwei", "drei", "vier", "fünf"])
    expect(at(page, "a").locator(".written.listed .row")).to_have_count(2)


@pytest.mark.parametrize("mode", ["copy", "row"])
def test_a_long_word_is_cut_and_pushes_no_word_off_its_row(editor, mode):
    page = editor(linked("a", "l4", mode, w=60, h=20), words=[LONG, "Hund"])
    rows = at(page, "a").locator(".written.listed .row")
    expect(rows).to_have_count(2)
    expect(rows.nth(1).locator("span").first).to_have_text("Hund")
    # A row is 10 mm high: the block's 60 mm are its measure of the page's scale.
    scale = at(page, "a").bounding_box()["width"] / 60
    first, second = rows.nth(0).bounding_box(), rows.nth(1).bounding_box()
    assert abs(first["height"] - 10 * scale) < 1, first
    assert abs(second["y"] - first["y"] - 10 * scale) < 1, (first, second)
    assert second["y"] >= first["y"]
    # The long word is wider than the block: it is cut at the right edge, not wrapped.
    expect(rows.nth(0).locator("span").first).to_have_text(LONG)
    assert rows.nth(0).locator("span").first.bounding_box()["width"] > 60 * scale


def test_blank_lines_and_commas_make_no_empty_row(editor):
    page = editor(linked("a", "l4", "copy", h=40), words=["Hund, Katze", "", "  ", "Maus"])
    rows = at(page, "a").locator(".written.listed .row")
    expect(rows).to_have_count(3)
    expect(rows.nth(0).locator("span")).to_have_text("Hund")
    expect(rows.nth(1).locator("span")).to_have_text("Katze")
    expect(rows.nth(2).locator("span")).to_have_text("Maus")


@pytest.mark.parametrize("words", ["Hund", 7, [1, None, {"a": 1}]])
def test_garbage_in_words_draws_as_none(editor, words):
    page = editor(linked("a", "l4", "copy", h=40), words=words)
    expect(at(page, "a").locator(".written.listed")).to_have_count(1)
    expect(page.locator(".written.listed .row")).to_have_count(0)
    expect(at(page, "a")).to_be_visible()


def test_a_linked_block_on_a_sheet_with_no_list_shows_empty_rows_and_not_its_own_text(editor):
    page = editor(
        box("a", "ruling", {"kind": "l4", "color": "#222", "list": "copy", "text": "eigen"}, h=40)
    )
    expect(at(page, "a").locator(".written.listed")).to_have_count(1)
    expect(at(page, "a")).not_to_contain_text("eigen")


def test_garbage_in_list_draws_as_none(editor):
    page = editor(
        box(
            "a",
            "ruling",
            {"kind": "l4", "color": "#222222", "list": "nonsense", "text": "eigen"},
            h=40,
        ),
        words=WORDS,
    )
    expect(page.locator(".written.listed")).to_have_count(0)
    expect(at(page, "a")).to_be_visible()
    expect(at(page, "a")).to_contain_text("eigen")


def test_the_own_text_rests_under_a_link(editor):
    page = editor(
        box(
            "a", "ruling", {"kind": "l4", "color": "#222222", "list": "copy", "text": "eigen"}, h=40
        ),
        words=["Hund"],
    )
    expect(at(page, "a")).to_contain_text("Hund")
    expect(at(page, "a")).not_to_contain_text("eigen")


@pytest.mark.parametrize("mode", MODES)
def test_karo_shows_a_letter_to_a_square(editor, mode):
    page = editor(
        box("a", "ruling", {"kind": "k5", "color": "#222222", "list": mode}, w=50, h=15),
        words=["Hund", "Katze"],
    )
    rows = at(page, "a").evaluate(SQUARES)
    if mode == "row":
        assert rows == ["Hund Hund", "Katze"], rows
    else:
        assert rows[:2] == ["Hund", "Katze"], rows
    fills = (
        at(page, "a")
        .locator("svg.ruling text")
        .evaluate_all("els => [...new Set(els.map((el) => el.getAttribute('fill')))]")
    )
    assert fills == (["currentColor"] if mode == "copy" else ["#aaaaaa"]), fills


def placed(shot, blank, row, count):
    """Where each row's word lies: the top of its ink and the middle of it, in px.

    `blank` is the same ruling with no word: the pixels it has dark are the lines, not ink.
    The lowest ink is no measure: a script's z has a tail below the baseline.
    """
    shot_img = Image.open(BytesIO(shot)).convert("L")
    blank_img = Image.open(BytesIO(blank)).convert("L")
    width, height = shot_img.size
    # One byte to a pixel in grey.
    shot_px, blank_px = shot_img.tobytes(), blank_img.tobytes()
    # The block is 90 mm wide.
    per_mm = width / 90
    found = []
    for i in range(count):
        ys = [
            y
            for y in range(round(i * row * per_mm), min(height, round((i + 1) * row * per_mm)))
            for x in range(width)
            if shot_px[y * width + x] < 100 and blank_px[y * width + x] > 200
        ]
        found.append((min(ys), sum(ys) / len(ys)) if ys else None)
    return found


@pytest.mark.parametrize("font", FONTS)
@pytest.mark.parametrize("kind", LINED)
def test_a_word_stands_where_a_typed_text_stands(editor, kind, font):
    # A typed text is a textarea, whose letters no range reaches, so the screenshots tell.
    props = {"kind": kind, "color": "#222222", "font": font}
    page = editor(
        box("typed", "ruling", {**props, "text": "Hund\nKatze"}, x=10, y=40, w=90, h=60),
        box("linked", "ruling", {**props, "list": "copy"}, x=110, y=40, w=90, h=60),
        box("blank", "ruling", props, x=10, y=120, w=90, h=60),
        words=["Hund", "Katze"],
    )
    page.evaluate("document.fonts.ready.then(() => 0)")
    blank = at(page, "blank").screenshot()
    typed = placed(at(page, "typed").screenshot(), blank, ROW[kind], 2)
    drawn = placed(at(page, "linked").screenshot(), blank, ROW[kind], 2)
    assert None not in typed + drawn, (typed, drawn)
    for (top, mid), (top2, mid2) in zip(typed, drawn, strict=True):
        assert abs(top - top2) <= 1 and abs(mid - mid2) <= 1, (typed, drawn)


def test_the_default_layout_reaches_the_list_from_the_bar(editor):
    """Blattform has no tabs in its panel: a button there leads to the list, with nothing picked
    and from a linked Lineatur, and Start in the bar leads back."""
    page = editor(linked("a", "l4", "copy", h=40))
    page.locator(".panel").get_by_role("button", name="Lernwörter", exact=True).click()
    field = page.get_by_label("Lernwörter", exact=True)
    field.press_sequentially("Hund")
    expect(at(page, "a").locator(".listed .row span")).to_have_text("Hund")
    page.locator(".modes").get_by_role("tab", name="Start").click()
    expect(field).to_have_count(0)
    pick(page, "a")
    page.get_by_role("button", name="Lernwörter bearbeiten").click()
    expect(field).to_have_value("Hund")
