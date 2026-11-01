"""Issue #857: Zeichenabstand on a text, a shape (Form) and a Lineatur.

`tracking` is extra space between letters as a share of the font size, from 0 to 1.
Absent draws as the font does. A cursive script warns that the joins break. Karo
keeps one letter in each square and has no control.
"""

import httpx
import pypdfium2
import pytest
from playwright.sync_api import expect
from test_painter import held, paint
from ui import FIELD, RECT, RULING, TEXT, at, box, pick, saved, unpick, user

WORD = "Mama"
WARN = "Zeichenabstand trennt die Verbindungen dieser Schreibschrift."
WIDE = {"tracking": 0.5}
# The share of an em the computed letter-spacing is, 0 when the font's own spacing stands.
SHARE = """(el) => {
    const s = getComputedStyle(el);
    return s.letterSpacing === "normal" ? 0 : parseFloat(s.letterSpacing) / parseFloat(s.fontSize);
}"""
# The width "Mama" takes in the field's own font and letter spacing. A Lineatur's shot
# also holds its rules, which run the whole width, so the letters are measured apart from them.
ADVANCE = """(el) => {
    const s = getComputedStyle(el);
    const probe = document.createElement("span");
    probe.style.cssText = "position:absolute;visibility:hidden;white-space:pre";
    probe.style.font = s.font;
    probe.style.letterSpacing = s.letterSpacing;
    probe.textContent = "Mama";
    document.body.append(probe);
    const w = probe.getBoundingClientRect().width;
    probe.remove();
    return w;
}"""
# The width of the word "Mama" in the block, in px of the screen.
SPAN = """(name) => {
    const block = document.querySelector(`.block[data-id="${name}"]`);
    const walker = document.createTreeWalker(block, NodeFilter.SHOW_TEXT);
    let node;
    while (walker.nextNode()) if (walker.currentNode.data.includes("Mama")) node = walker.currentNode;
    const range = document.createRange();
    const i = node.data.indexOf("Mama");
    range.setStart(node, i);
    range.setEnd(node, i + 4);
    return range.getBoundingClientRect().width;
}"""


def share(page, name, selector):
    return at(page, name).locator(selector).evaluate(SHARE)


def span(page, name):
    return page.evaluate(SPAN, name)


def ink_span(img):
    """The width in px of the dark ink, from its leftmost dark pixel to its rightmost."""
    grey = img.convert("L")
    w = grey.width
    left, right = w, -1
    for i, v in enumerate(grey.tobytes()):
        if v < 160:
            x = i % w
            left = min(left, x)
            right = max(right, x)
    return 0 if right < left else right - left + 1


def pdf_ink(picture, box_mm):
    """The ink width in mm of a crop of the printed page, `box_mm` as x, y, w, h."""
    per = picture.height / 297
    x, y, w, h = box_mm
    crop = picture.crop((int(x * per), int(y * per), int((x + w) * per), int((y + h) * per)))
    return ink_span(crop) / per


# What each kind draws "Mama" in, and the element that carries the letter spacing.
KINDS = [
    ("text", {**TEXT, "text": WORD, "size": 36}, ".frame"),
    ("shape", {**RECT, "stroke": "none", "fill": "none", "text": WORD, "size": 36}, ".frame"),
    ("ruling", {**RULING, "text": WORD}, "textarea.written"),
]


@pytest.mark.parametrize("kind,props,selector", KINDS)
def test_spaced_letters_are_wider_on_the_sheet(editor, kind, props, selector):
    """A text, a shape and a Lineatur with tracking 0.5 draw Mama wider than the same without it."""
    page = editor(
        box("plain", kind, props, x=15, y=30, w=100, h=30),
        box("wide", kind, {**props, **WIDE}, z=2, x=120, y=30, w=100, h=30),
    )
    unpick(page)
    assert abs(share(page, "plain", selector)) < 0.02
    assert abs(share(page, "wide", selector) - 0.5) < 0.02
    if kind == "ruling":
        plain = at(page, "plain").locator(selector).evaluate(ADVANCE)
        wide = at(page, "wide").locator(selector).evaluate(ADVANCE)
    else:
        plain, wide = span(page, "plain"), span(page, "wide")
    assert wide > plain * 1.25, (kind, plain, wide)


@pytest.mark.parametrize("kind,props", [(k, p) for k, p, _ in KINDS])
def test_the_slider_sets_letter_spacing_and_undo_clears_it(editor, kind, props):
    """The Zeichenabstand slider stores the share, and one undo takes it off."""
    client = user()
    page = editor(box("a", kind, props, w=120, h=30), client=client)
    pick(page, "a")
    slider = page.locator(".panel").get_by_label("Zeichenabstand", exact=True)
    expect(slider).to_have_value("0")
    slider.fill("0.4")
    expect(slider).to_have_value("0.4")
    assert saved(page, client)[0]["props"]["tracking"] == 0.4
    page.get_by_label("Rückgängig", exact=True).click()
    expect(slider).to_have_value("0")
    assert "tracking" not in saved(page, client)[0]["props"]


@pytest.mark.parametrize(
    "font,warns",
    [
        ("andika", False),
        ("nord", False),
        ("sued", False),
        ("grund", False),
        ("urff", False),
        ("va", True),
        ("sas", True),
        ("la", True),
    ],
)
def test_only_a_cursive_script_warns_that_the_joins_break(editor, font, warns):
    """VA, SAS and LA warn once the letters are spaced. Print and Grundschrift do not."""
    page = editor(box("a", "text", {**TEXT, "font": font, "tracking": 0.2}))
    pick(page, "a")
    hint = page.locator(".panel").get_by_text(WARN)
    if warns:
        expect(hint).to_be_visible()
    else:
        expect(hint).to_have_count(0)


def test_a_cursive_lineatur_warns_and_a_print_one_does_not(editor):
    """The Lineatur's own slider warns for Schulausgangsschrift and stays quiet for Druckschrift."""
    page = editor(
        box("print", "ruling", {**RULING, "text": WORD, "tracking": 0.2}, x=15, y=25, w=120, h=20),
        box(
            "script",
            "ruling",
            {**RULING, "text": WORD, "font": "sas", "tracking": 0.2},
            z=2,
            x=15,
            y=70,
            w=120,
            h=20,
        ),
    )
    pick(page, "print")
    expect(page.locator(".panel").get_by_text(WARN)).to_have_count(0)
    pick(page, "script")
    expect(page.locator(".panel").get_by_text(WARN)).to_be_visible()


def test_picking_a_cursive_script_warns_until_the_spacing_is_off(editor):
    """With the letters spaced, choosing a cursive script shows the warning, and 0 hides it."""
    client = user()
    page = editor(box("a", "text", {**TEXT, "tracking": 0.2}), client=client)
    pick(page, "a")
    expect(page.locator(".panel").get_by_text(WARN)).to_have_count(0)
    page.get_by_label("Schriftart", exact=True).click()
    page.get_by_role("listbox", name="Liste: Schriftart").get_by_role(
        "option", name="Schulausgangsschrift", exact=True
    ).click()
    expect(page.locator(".panel").get_by_text(WARN)).to_be_visible()
    page.locator(".panel").get_by_label("Zeichenabstand", exact=True).fill("0")
    expect(page.locator(".panel").get_by_text(WARN)).to_have_count(0)
    assert saved(page, client)[0]["props"]["tracking"] == 0
    assert share(page, "a", ".frame") == 0


def test_no_spacing_on_a_cursive_script_does_not_warn(editor):
    """The warning is about the spacing, not about the script on its own."""
    page = editor(box("a", "text", {**TEXT, "font": "la"}))
    pick(page, "a")
    expect(page.locator(".panel").get_by_text(WARN)).to_have_count(0)


@pytest.mark.parametrize("kind", ["k5", "k7"])
def test_karo_has_no_letter_spacing_control_and_keeps_its_squares(editor, kind):
    """Karo has no Zeichenabstand. A stored share does not move a letter out of its square."""
    row = 5 if kind == "k5" else 7
    size = row * 0.75
    page = editor(
        box("a", "ruling", {"kind": kind, "color": "#222222", "text": WORD, **WIDE}, w=80, h=40)
    )
    pick(page, "a")
    expect(page.locator(".panel").get_by_label("Zeichenabstand", exact=True)).to_have_count(0)
    # The field's spacing is the square's, (row - 0.6 size) over the font size, not half an em.
    got = share(page, "a", "textarea.written")
    assert abs(got - (row - 0.6 * size) / size) < 0.05
    assert abs(got - 0.5) > 0.1


def test_lernwoerter_on_a_lineatur_take_the_letter_spacing(editor):
    """A Lineatur that copies the Lernwörter spaces those words the same way."""
    page = editor(
        box("plain", "ruling", {**RULING, "list": "copy"}, w=160, h=20),
        box("wide", "ruling", {**RULING, "list": "copy", **WIDE}, z=2, y=50, w=160, h=20),
        words=["Mama"],
    )
    unpick(page)
    assert span(page, "wide") > span(page, "plain") * 1.25


def test_the_open_text_keeps_the_letter_spacing(editor):
    """Typing in the text keeps the spacing the sheet draws."""
    page = editor(box("a", "text", {**TEXT, "tracking": 0.4}))
    pick(page, "a")
    page.keyboard.press("Enter")
    expect(page.locator(FIELD)).to_be_focused()
    assert abs(page.locator(FIELD).evaluate(SHARE) - 0.4) < 0.02


def test_the_number_before_a_text_stays_tight(editor):
    """The numbering beside a spaced text keeps the font's own spacing."""
    page = editor(box("a", "text", {**TEXT, "text": WORD, "size": 36, **WIDE}, mark="1."))
    unpick(page)
    assert abs(share(page, "a", ".frame") - 0.5) < 0.02
    assert share(page, "a", ".mark") == 0


def test_a_syllable_bow_grows_with_the_letters(editor):
    """A Silbenbogen follows the wider syllable."""
    props = {**TEXT, "text": WORD, "size": 28, "syllables": True}
    page = editor(
        box("plain", "text", props, w=80, h=24),
        box("wide", "text", {**props, **WIDE}, z=2, x=110, w=80, h=24),
    )
    expect(at(page, "plain").locator(".unsplit")).to_have_count(0)
    expect(at(page, "wide").locator(".unsplit")).to_have_count(0)

    def bow(name):
        return at(page, name).locator(".syl").first.evaluate("el => el.getBBox().width")

    assert bow("wide") > bow("plain") * 1.2


def test_the_brush_carries_letter_spacing_and_can_clear_it(editor):
    """Format übertragen takes the share onto a text, a shape and a Lineatur, and a plain text clears it."""
    client = user()
    page = editor(
        box("a", "text", {**TEXT, "tracking": 0.4}, x=15, y=20, w=40, h=16),
        box("b", "text", TEXT, z=2, x=70, y=20, w=40, h=16),
        box("form", "shape", {**RECT, "text": "Hallo"}, z=3, x=125, y=20, w=50, h=24),
        box("lines", "ruling", {**RULING, "text": WORD}, z=4, x=15, y=70, w=120, h=20),
        box("plain", "text", TEXT, z=5, x=70, y=110, w=40, h=16),
        box("set", "text", {**TEXT, "tracking": 0.4}, z=6, x=15, y=110, w=40, h=16),
        client=client,
    )
    paint(page, "a", "b")
    paint(page, "a", "form")
    paint(page, "a", "lines")
    now = held(page, client)
    assert now["b"]["tracking"] == now["form"]["tracking"] == now["lines"]["tracking"] == 0.4
    paint(page, "plain", "set")
    assert "tracking" not in held(page, client)["set"]


@pytest.mark.parametrize("tracking", ["weit", -0.2])
def test_a_spacing_the_sheet_does_not_know_draws_as_the_font(editor, tracking):
    """A share that is no number, or below 0, draws with the font's own spacing."""
    page = editor(box("a", "text", {**TEXT, "text": WORD, "size": 28, "tracking": tracking}, w=100))
    unpick(page)
    assert share(page, "a", ".frame") == 0


def test_a_spacing_past_one_draws_as_one(editor):
    """A share above 1 draws as 1, the top of the slider."""
    page = editor(
        box("over", "text", {**TEXT, "text": WORD, "size": 28, "tracking": 4}, w=140, h=24),
        box(
            "one", "text", {**TEXT, "text": WORD, "size": 28, "tracking": 1}, z=2, y=50, w=140, h=24
        ),
    )
    unpick(page)
    assert abs(share(page, "over", ".frame") - 1) < 0.02
    assert abs(share(page, "one", ".frame") - share(page, "over", ".frame")) < 0.02


def test_the_pdf_prints_the_letters_further_apart(editor, server):
    """The printed sheet spaces a text, a shape and the letters on a Lineatur."""
    client = user()
    # The Lineatur's lines run the width of the block. The crop is the band of the letters,
    # above Lineatur 4's writing line at 10 mm, so the line itself is not the ink.
    blocks = []
    for i, (kind, props, _) in enumerate(KINDS):
        y = 20 + 40 * i
        blocks.append(box("plain" + kind, kind, props, x=15, y=y, w=90, h=24))
        blocks.append(box("wide" + kind, kind, {**props, **WIDE}, z=i + 2, x=120, y=y, w=90, h=24))
    page = editor(*blocks, client=client)
    unpick(page)
    sheet_id = page.url.rsplit("/", 1)[1]
    cookie = {"Cookie": f"session={client.cookies['session']}"}
    res = httpx.get(f"{server}/api/sheets/{sheet_id}/pdf", headers=cookie, timeout=90)
    assert res.status_code == 200
    picture = pypdfium2.PdfDocument(res.content)[0].render(scale=4).to_pil().convert("L")
    for i, (kind, _, _) in enumerate(KINDS):
        y = 20 + 40 * i
        band = (15, y + 1, 70, 8) if kind == "ruling" else (15, y, 80, 20)
        plain = pdf_ink(picture, band)
        wide = pdf_ink(picture, (band[0] + 105, band[1], band[2], band[3]))
        assert wide > plain * 1.2, (kind, plain, wide)
