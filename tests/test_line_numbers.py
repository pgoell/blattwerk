"""Zeilennummerierung: the grey numbers beside a text's lines, counted as they break (issue #63).

The docstrings name the lines of the checklist for the feature: A is the drawing, I the editor's
own ways of changing a text. The numbers are measured, as the bows are, so each test waits until
`unsplit` has gone before it asks where a number stands.
"""

import io
import re

import pytest
from PIL import Image
from playwright.sync_api import expect
from ui import LINE, RECT, TABLE, TEXT, apart, at, box, pick

LONG = (
    "Der kleine Igel sucht im Herbst unter den Bäumen nach Futter und baut sich aus Laub ein "
    "warmes Nest. Die Eichhörnchen sammeln Nüsse und verstecken sie überall im Garten, damit "
    "sie im Winter genug zu fressen haben. Manchmal vergessen sie ein Versteck, und im "
    "Frühling wächst dort ein neuer Baum. Die Vögel ziehen in den Süden."
)
GREY = "rgb(112, 112, 112)"
# The visual lines of a block's text, top to bottom, measured another way than the app does: each
# letter alone, and a line is where the letters' tops agree. A space is no letter: WebKit gives
# the space a line ends with a rect of its own.
LINES = """(block) => {
    const rows = [];
    const frame = block.querySelector(":scope > .frame");
    const walk = document.createTreeWalker(frame, NodeFilter.SHOW_TEXT);
    const range = document.createRange();
    while (walk.nextNode()) {
        const node = walk.currentNode;
        if (node.parentElement.closest("textarea, .bank")) continue;
        for (let i = 0; i < node.data.length; i++) {
            if (!node.data[i].trim()) continue;
            range.setStart(node, i);
            range.setEnd(node, i + 1);
            const rect = range.getClientRects()[0];
            if (rect && !rows.some(([top]) => Math.abs(top - rect.top) < 2))
                rows.push([rect.top, rect.bottom]);
        }
    }
    return rows.sort((a, b) => a[0] - b[0]);
}"""


def lines(page, name):
    """The visual lines of the block's text, as [top, bottom] on the screen, in order."""
    expect(at(page, name).locator(".unsplit")).to_have_count(0)
    return at(page, name).evaluate(LINES)


def beside(page, name):
    """Each number with the index of the line it stands beside (None if none), and its right edge.

    A number stands beside a line when the middle of its box lies between the line's top and
    bottom.
    """
    found = lines(page, name)
    boxes = (
        at(page, name)
        .locator(".ln")
        .evaluate_all(
            "els => els.map((el) => { const r = el.getBoundingClientRect();"
            " return [el.textContent, (r.top + r.bottom) / 2, r.right]; })"
        )
    )
    return [
        (
            text,
            next((i for i, (top, bottom) in enumerate(found) if top < middle < bottom), None),
            right,
        )
        for text, middle, right in boxes
    ]


def rect(found):
    """The box of a number on the screen. WebKit has none for Playwright's own `bounding_box`."""
    return found.evaluate(
        "el => { const r = el.getBoundingClientRect();"
        " return {x: r.left, y: r.top, width: r.width, height: r.height}; }"
    )


def texts(page, name):
    """The numbers as they read, in order."""
    return [text for text, _, _ in beside(page, name)]


def lowest_dark_row(png):
    """The lowest row of a picture with a dark pixel in it."""
    grey = Image.open(io.BytesIO(png)).convert("L")
    data, width = grey.tobytes(), grey.width
    for y in reversed(range(grey.height)):
        if min(data[y * width : (y + 1) * width]) < 128:
            return y
    return -1


def test_numbers_count_the_lines_as_they_break(editor):
    """A6, A8a: a long paragraph in an 80 mm box: a number beside each line it breaks into."""
    page = editor(box("a", "text", {**TEXT, "text": LONG, "lines": 1}, w=80, h=120))
    found = lines(page, "a")
    assert len(found) > 3
    assert texts(page, "a") == [str(n) for n in range(1, len(found) + 1)]
    left = at(page, "a").bounding_box()["x"]
    for text, index, right in beside(page, "a"):
        assert index == int(text) - 1, (text, index)
        assert right < left


def test_every_fifth_line_gets_a_number(editor):
    """A7: with `lines` at 5, the fifth line has 5, the tenth 10: no other line has one."""
    page = editor(box("a", "text", {**TEXT, "text": LONG, "lines": 5}, w=80, h=120))
    found = lines(page, "a")
    assert len(found) >= 10
    assert texts(page, "a") == [str(5 * n) for n in range(1, len(found) // 5 + 1)]
    assert beside(page, "a")[0][1] == 4


def test_an_empty_line_does_not_count(editor):
    """A8b: an empty line between two paragraphs is no line: "zwei" is the second."""
    page = editor(box("a", "text", {**TEXT, "text": "eins\n\nzwei", "lines": 1}))
    assert texts(page, "a") == ["1", "2"]
    assert beside(page, "a")[1][1] == 1


def test_a_line_of_spaces_alone_does_not_count(editor):
    """A8b: three spaces between two paragraphs are an empty line too."""
    page = editor(box("a", "text", {**TEXT, "text": "eins\n   \nzwei", "lines": 1}))
    expect(at(page, "a").locator(".unsplit")).to_have_count(0)
    assert at(page, "a").locator(".ln").all_text_contents() == ["1", "2"]
    # "zwei" stands on the third line of the text: its number lies two lines below the first.
    # In the block's own pixels: WebKit gives no box of its own for a text of an SVG.
    line = at(page, "a").locator(".frame p").first.evaluate("el => el.offsetHeight / 3")
    first, second = (float(at(page, "a").locator(".ln").nth(i).get_attribute("y")) for i in (0, 1))
    assert abs(second - first - 2 * line) < 2


@pytest.mark.parametrize("font", ["andika", "grund", "va", "sas", "la"])
def test_every_script_has_a_number_for_each_line_at_the_tightest_spacing(editor, font):
    """A8a: counted by a second measure, the paragraph's height over the height of a line."""
    look = {**TEXT, "text": LONG, "lines": 1, "font": font, "spacing": 1}
    page = editor(box("a", "text", look, w=80, h=200))
    expect(at(page, "a").locator(".unsplit")).to_have_count(0)
    # In the block's own pixels: the zoom scales the paragraph's box on the screen.
    rows = (
        at(page, "a")
        .locator(".frame p")
        .evaluate("el => el.offsetHeight / parseFloat(getComputedStyle(el).lineHeight)")
    )
    assert round(rows) > 3
    expect(at(page, "a").locator(".ln")).to_have_count(round(rows))


def test_small_grey_print_font_on_the_baseline(editor):
    """A10: Andika whatever the font, grey, 0.7 of the text's size, on the text's baseline."""
    page = editor(
        box("a", "text", {**TEXT, "text": "HEHE", "size": 28, "font": "grund", "lines": 1})
    )
    number = at(page, "a").locator(".ln")
    # The number is drawn anew when the script comes in: the one to read is the one that stays.
    page.evaluate("document.fonts.ready")
    expect(at(page, "a").locator(".unsplit")).to_have_count(0)
    expect(number).to_have_count(1)
    style = number.evaluate(
        "el => { const s = getComputedStyle(el); return { family: s.fontFamily, fill: s.fill,"
        " size: parseFloat(s.fontSize) }; }"
    )
    text_size = (
        at(page, "a").locator(".frame").evaluate("el => parseFloat(getComputedStyle(el).fontSize)")
    )
    assert "Andika" in style["family"]
    assert style["fill"] == GREY
    assert abs(style["size"] - 0.7 * text_size) < 0.1
    # The number and the letters, each cut from the picture: the lowest dark row of each.
    block = at(page, "a").bounding_box()
    mark = rect(number)
    number_ink = lowest_dark_row(
        page.screenshot(
            clip={
                "x": mark["x"] - 2,
                "y": block["y"],
                "width": mark["width"] + 4,
                "height": block["height"],
            }
        )
    )
    letters_ink = lowest_dark_row(page.screenshot(clip=block))
    assert abs(number_ink - letters_ink) <= 1, (number_ink, letters_ink)


def test_the_numbers_follow_the_font_size_the_width_and_the_spacing(editor):
    """A9: a bigger font and a narrower box give more lines their numbers, still beside them."""
    page = editor(box("a", "text", {**TEXT, "text": LONG, "lines": 1}, w=80, h=200))
    pick(page, "a")
    before = len(texts(page, "a"))
    for _ in range(3):
        page.get_by_label("Schrift größer", exact=True).click()
    bigger = texts(page, "a")
    assert len(bigger) > before
    assert [index for _, index, _ in beside(page, "a")] == list(range(len(bigger)))
    page.get_by_label("Breite", exact=True).fill("40")
    page.get_by_label("Breite", exact=True).press("Enter")
    assert len(texts(page, "a")) > len(bigger)


def test_the_numbers_follow_the_line_spacing(editor):
    """A9: lines set further apart take their numbers down with them."""
    page = editor(box("a", "text", {**TEXT, "text": LONG, "lines": 1}, w=80, h=200))
    pick(page, "a")
    count = len(texts(page, "a"))

    def second():
        return rect(at(page, "a").locator(".ln").nth(1))["y"]

    before = second()
    slider = page.locator(".panel").get_by_label("Zeilenabstand", exact=True)
    slider.focus()
    for _ in range(5):
        page.keyboard.press("ArrowRight")
    expect(slider).to_have_value("1.8")
    assert [index for _, index, _ in beside(page, "a")] == list(range(count))
    assert second() > before + 5


def test_numbers_follow_the_text_as_it_is_typed(editor):
    """I2: typed in the field, the numbers grow with the lines; an empty paragraph is none."""
    page = editor(box("a", "text", {**TEXT, "text": "Hallo", "lines": 1}))
    pick(page, "a")
    page.keyboard.press("Enter")
    page.keyboard.type(LONG[:200])
    page.keyboard.press("Enter")
    page.keyboard.press("Enter")
    page.keyboard.type("Ende")
    expect(page.locator(".block.sel .ProseMirror")).to_contain_text("Ende")
    expect(at(page, "a").locator(".ln")).to_have_count(len(lines(page, "a")))


def test_a_line_cut_off_below_the_box_has_no_number(editor):
    """I3: a text too long for its box, which stays 12 mm high: its last lines are cut off."""
    page = editor(box("a", "text", {**TEXT, "text": LONG, "lines": 1}, w=60, h=12))
    # The block's own pixels, not its box on the screen, which the zoom scales.
    assert (
        abs(
            float(at(page, "a").evaluate("el => el.style.height").removesuffix("px"))
            - 12 * 96 / 25.4
        )
        < 0.1
    )
    block = at(page, "a").bounding_box()
    found = lines(page, "a")
    shown = texts(page, "a")
    assert 0 < len(shown) < len(found)
    bottom = block["y"] + block["height"]
    # A number's middle lies in the box, as a line's does.
    middles = (
        at(page, "a")
        .locator(".ln")
        .evaluate_all(
            "els => els.map((el) => { const r = el.getBoundingClientRect();"
            " return (r.top + r.bottom) / 2; })"
        )
    )
    for middle in middles:
        assert middle <= bottom


def test_a_turned_block_turns_its_numbers_with_it(editor):
    """I4: a block turned 30 degrees has its numbers where the level one has them, turned too."""
    level = box("a", "text", {**TEXT, "text": LONG, "lines": 1}, w=80, h=40)
    turned = box("b", "text", {**TEXT, "text": LONG, "lines": 1}, w=80, h=40, angle=30)
    page = editor(*apart(turned, level))
    assert at(page, "b").locator(":scope > svg.numbers").count() == 1
    svg_y = "els => els.map((el) => [el.textContent, el.getAttribute('y')])"
    assert at(page, "a").locator(".ln").evaluate_all(svg_y) == at(page, "b").locator(
        ".ln"
    ).evaluate_all(svg_y)
    assert at(page, "b").evaluate("el => el.style.transform").startswith("rotate")


def test_the_mark_stands_left_of_the_numbers(editor):
    """I5: the block's mark lies left of the column of numbers, and no number is under it."""
    page = editor(box("a", "text", {**TEXT, "text": LONG, "lines": 1}, w=80, h=60, mark="1."))
    expect(at(page, "a").locator(".mark")).to_be_visible()
    # The mark's letters, not its box: the box keeps the column of numbers as padding on its right.
    letters = (
        at(page, "a")
        .locator(".mark")
        .evaluate(
            "el => { const range = document.createRange(); range.selectNodeContents(el);"
            " const r = range.getBoundingClientRect(); return [r.left, r.right]; }"
        )
    )
    numbered = (
        at(page, "a")
        .locator(".ln")
        .evaluate_all(
            "els => els.map((el) => { const r = el.getBoundingClientRect();"
            " return [r.left, r.right]; })"
        )
    )
    assert numbered
    for left, right in numbered:
        assert letters[1] < left
        assert right <= at(page, "a").bounding_box()["x"]


def test_the_numbers_take_no_click_and_are_no_text(editor):
    """I6: a click on a number selects nothing; the numbers are no words of the text."""
    page = editor(box("a", "text", {**TEXT, "text": "Hallo", "lines": 1}))
    expect(at(page, "a").locator(".ln")).to_have_count(1)
    number = rect(at(page, "a").locator(".ln"))
    page.mouse.click(number["x"] + number["width"] / 2, number["y"] + number["height"] / 2)
    expect(at(page, "a")).not_to_have_class(re.compile("sel"))
    assert not any(ch.isdigit() for ch in at(page, "a").locator(".frame").inner_text())


@pytest.mark.parametrize(
    "look",
    [
        pytest.param({"valign": "bottom"}, id="bottom"),
        pytest.param({"valign": "middle"}, id="middle"),
        pytest.param({"fill": "#ffd43b", "stroke": "#222222", "strokeWidth": 1}, id="framed"),
    ],
)
def test_beside_their_lines_at_the_bottom_in_the_middle_and_in_a_frame(editor, look):
    """I7: a box much higher than its two lines: each number beside its own line."""
    page = editor(box("a", "text", {**TEXT, "text": "eins\nzwei", "lines": 1, **look}, h=60))
    assert [(text, index) for text, index, _ in beside(page, "a")] == [("1", 0), ("2", 1)]


@pytest.mark.parametrize(
    "kind, props",
    [
        pytest.param("shape", {**RECT, "text": "Hallo du", "lines": 1}, id="shape"),
        pytest.param("shape", {**LINE, "lines": 1}, id="line"),
        pytest.param("table", {**TABLE, "lines": 1}, id="table"),
    ],
)
def test_only_a_text_takes_numbers(editor, kind, props):
    """A13: a shape, a line or a table with a stray `lines` shows no numbers."""
    page = editor(box("a", kind, props))
    expect(at(page, "a")).to_be_visible()
    expect(at(page, "a").locator(".numbers")).to_have_count(0)


def test_a_text_in_a_group_takes_numbers(editor):
    """A13: a text that is a member of a group shows its numbers."""
    page = editor(
        box("a", "text", {**TEXT, "text": "Fenster", "lines": 1}, group=["g"]),
        box("b", "shape", {**RECT, "text": "Wasser"}, z=2, group=["g"]),
    )
    expect(at(page, "a").locator(".ln")).to_have_count(1)


@pytest.mark.parametrize(
    "lines",
    [None, 0, -1, 2.5, "5", True, 101],
    ids=["absent", "zero", "minus", "half", "text", "true", "too-big"],
)
def test_no_step_no_numbers(editor, lines):
    """A15: no whole number from 1 to 100 means no numbers; the text shows."""
    props = (
        {**TEXT, "text": "Hallo"} if lines is None else {**TEXT, "text": "Hallo", "lines": lines}
    )
    page = editor(box("a", "text", props))
    expect(at(page, "a")).to_contain_text("Hallo")
    expect(at(page, "a").locator(".numbers")).to_have_count(0)


def test_numbers_with_a_list_count_the_lines_and_stand_left_of_the_box(editor):
    """A14, lists: one number per line of the list, all of them left of the box."""
    rich = [{"runs": [{"text": LONG}], "list": "number"}]
    page = editor(box("a", "text", {**TEXT, "text": LONG, "rich": rich, "lines": 1}, w=80, h=120))
    found = lines(page, "a")
    assert texts(page, "a") == [str(n) for n in range(1, len(found) + 1)]
    block = at(page, "a").bounding_box()
    assert all(right < block["x"] for _, _, right in beside(page, "a"))
    assert at(page, "a").locator(".frame p").first.bounding_box()["x"] >= block["x"]


def test_numbers_with_bows_and_colours_count_the_same_lines(editor):
    """A14, bows and colours: the same lines as with no numbers, and the bows drawn."""
    plain = {**TEXT, "text": LONG, "syllables": True, "tints": ["#1a56db", "#e02424"]}
    page = editor(
        box("a", "text", plain, w=80, h=120),
        box("b", "text", {**plain, "lines": 1}, z=2, w=80, h=120),
    )
    expect(at(page, "b").locator(".ln").first).to_be_visible()
    assert len(lines(page, "a")) == len(lines(page, "b"))
    assert len(texts(page, "b")) == len(lines(page, "b"))
    assert at(page, "b").locator(".syl").count() > 0


def test_numbers_with_gaps_count_the_same_lines_with_and_without_a_bank(editor):
    """A14, gaps: a gap is part of its line, and a box of solution words moves no line."""
    rich = [
        {
            "runs": [
                {"text": "Der "},
                {"text": "Hund", "gap": True},
                {"text": " bellt laut und die Katze schläft"},
            ]
        }
    ]
    base = {
        **TEXT,
        "text": "Der Hund bellt laut und die Katze schläft",
        "rich": rich,
        "gapWidth": 12,
        "lines": 1,
    }
    page = editor(
        box("a", "text", base, w=80, h=60),
        box("b", "text", {**base, "bank": 7}, z=2, w=80, h=60),
    )
    expect(at(page, "b").locator(".ln").first).to_be_visible()
    assert texts(page, "a") == texts(page, "b")
    assert len(texts(page, "a")) >= 1
