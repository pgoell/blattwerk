"""Lückentext: a gap is a line as wide as its words, the words are shown grey in the editor,
hidden on the pupil's sheet and shown in the answer key, and the box of solution words stands
under the text.

The docstrings name the lines of the checklist for the feature.
"""

import io

import httpx
import pytest
from playwright.sync_api import expect
from pypdf import PdfReader
from ui import TABLE, TEXT, at, block, box, sheet, syls, tints, user

GAP = {
    **TEXT,
    "text": "Der Hund bellt",
    "rich": [{"runs": [{"text": "Der "}, {"text": "Hund", "gap": True}, {"text": " bellt"}]}],
}
PLAIN = {**TEXT, "text": "Der Hund bellt", "rich": [{"runs": [{"text": "Der Hund bellt"}]}]}
# Three gaps in reading order; seed 1 shuffles them to another order.
WORDS = {
    **TEXT,
    "text": "Der Hund bellt. Die Katze miaut. Die Maus pfeift.",
    "rich": [
        {
            "runs": [
                {"text": "Der "},
                {"text": "Hund", "gap": True},
                {"text": " bellt. Die "},
                {"text": "Katze", "gap": True},
                {"text": " miaut. Die "},
                {"text": "Maus", "gap": True},
                {"text": " pfeift."},
            ]
        }
    ],
    "bank": 1,
}
GARBAGE = [
    ("text", {**GAP, "rich": [{"runs": [{"text": "Der "}, {"text": "Hund", "gap": "yes"}]}]}),
    ("text", {**GAP, "bank": "x"}),
    ("text", {**GAP, "gapWidth": -5}),
    ("table", {**TABLE, "gaps": "x"}),
]

# A gap's box and the word "Hund" in the plain text of another block, in px; and the gap's line.
WIDTHS = """([gap, plain]) => {
    const span = document.querySelector(`.block[data-id="${gap}"] .gap`);
    const rich = document.querySelector(`.block[data-id="${plain}"] .rich`);
    const walk = document.createTreeWalker(rich, NodeFilter.SHOW_TEXT);
    let text;
    while (walk.nextNode()) if (walk.currentNode.data.includes("Hund")) text = walk.currentNode;
    const range = document.createRange();
    const from = text.data.indexOf("Hund");
    range.setStart(text, from);
    range.setEnd(text, from + 4);
    const line = getComputedStyle(span);
    return {
        gap: span.getBoundingClientRect().width,
        word: range.getBoundingClientRect().width,
        border: line.borderBottomStyle + " " + line.borderBottomWidth,
    };
}"""


def test_a_gap_is_a_line_as_wide_as_its_words(editor):
    """A1: the gap's box is as wide as the same word without the flag, and its line is drawn."""
    page = editor(box("a", "text", GAP), box("b", "text", PLAIN, z=2))
    widths = page.evaluate(WIDTHS, ["a", "b"])
    assert abs(widths["gap"] - widths["word"]) <= 1
    assert widths["border"] != "none 0px"


def test_with_gap_width_every_gap_is_as_wide_and_a_longer_word_widens_its_own(editor):
    """A3: with gapWidth, the short gaps of a block are equally wide; a longer word is wider."""
    props = {
        **TEXT,
        "gapWidth": 30,
        "text": "a Hund Elefantenherdenstampede",
        "rich": [
            {"runs": [{"text": "a", "gap": True}, {"text": " "}, {"text": "Hund", "gap": True}]},
            {"runs": [{"text": "Elefantenherdenstampede", "gap": True}]},
        ],
    }
    page = editor(box("a", "text", props))
    measure = "els => els.map((el) => el.getBoundingClientRect().width)"
    widths = at(page, "a").locator(".gap").evaluate_all(measure)
    assert abs(widths[0] - widths[1]) <= 1
    assert widths[2] > widths[0] + 1


def test_the_editor_shows_a_gap_word_in_grey(editor):
    """A5: the editor greys a gap's words in the drawn text."""
    page = editor(box("a", "text", GAP))
    color = at(page, "a").locator(".gap > span").evaluate("el => getComputedStyle(el).color")
    assert color == "rgb(153, 153, 153)"


def test_a_box_of_solution_words_stands_under_the_text_in_a_seeded_order(editor):
    """A7: the box holds each hidden word once, out of reading order, the same after a reload and
    in another block with the same seed; another seed gives another order."""
    page = editor(
        box("a", "text", WORDS),
        box("b", "text", WORDS, z=2),
        box("c", "text", {**WORDS, "bank": 2}, z=3),
    )
    order = at(page, "a").locator(".bank span").all_inner_texts()
    assert sorted(order) == ["Hund", "Katze", "Maus"]
    assert order != ["Hund", "Katze", "Maus"]
    assert at(page, "b").locator(".bank span").all_inner_texts() == order
    assert at(page, "c").locator(".bank span").all_inner_texts() != order
    page.reload()
    expect(at(page, "a").locator(".bank span").first).to_be_visible()
    assert at(page, "a").locator(".bank span").all_inner_texts() == order


def test_a_gap_cell_of_a_table_draws_as_a_gap(editor):
    """A13: a table's gap cell draws its line and its word."""
    page = editor(box("t", "table", {**TABLE, "gaps": [[True, False], [False, False]]}))
    expect(at(page, "t").locator(".gap > span").first).to_have_text("H")


@pytest.mark.parametrize(
    "kind,props",
    [
        ("text", GAP),
        ("shape", {**GAP, "kind": "rect", "stroke": "#222222", "strokeWidth": 0.5, "fill": "none"}),
        ("table", {**TABLE, "gaps": [[True, False], [False, False]]}),
    ],
    ids=["text", "shape", "table"],
)
def test_a_stored_gap_draws_as_a_gap_in_text_shape_and_table(editor, kind, props):
    """A13: a stored gap draws as a gap, in a text, a shape with text and a table."""
    page = editor(box("a", kind, props))
    expect(at(page, "a").locator(".gap")).to_have_count(1)


def test_a_gap_word_has_no_bow_and_no_colour_in_the_editor(editor):
    """A14: a gap's syllables get no bow and no colour; the syllables after it keep theirs."""
    paired = {**TEXT, "syllables": True, "tints": ["#1a56db", "#e02424"]}
    gapped = {
        **paired,
        "text": "Der Katze laut",
        "rich": [{"runs": [{"text": "Der "}, {"text": "Katze", "gap": True}, {"text": " laut"}]}],
    }
    plain = {**paired, "text": "Der Katze laut", "rich": [{"runs": [{"text": "Der Katze laut"}]}]}
    only = {**paired, "text": "Katze", "rich": [{"runs": [{"text": "Katze"}]}]}
    blocks = [box("a", "text", gapped), box("b", "text", plain, z=2), box("c", "text", only, z=3)]
    page = editor(*blocks)
    katze = syls(page, "c")
    assert syls(page, "a") == [s for s in syls(page, "b") if s not in katze]
    assert tints(page, "a") == [t for t in tints(page, "b") if t[0] not in katze]


@pytest.mark.parametrize("kind,props", GARBAGE, ids=["gap", "bank", "width", "gaps"])
def test_garbage_in_the_gaps_shows_the_text_and_breaks_nothing(editor, kind, props):
    """Garbage: a gap, bank, gapWidth or gaps of the wrong kind shows the text, breaks nothing"""
    page = editor(box("a", kind, props))
    faults = []
    page.on("pageerror", lambda fault: faults.append(fault))
    expect(at(page, "a")).to_contain_text("Hund" if kind == "text" else "H")
    assert not faults


def test_the_answer_key_pdf_holds_the_hidden_word_and_the_pupils_does_not(server):
    """A9: the PDF of the answer key prints the hidden word, the pupil's sheet does not."""
    client = user()
    mine = sheet(client, [block("text", 15, 40, GAP)])
    cookie = {"Cookie": f"session={client.cookies['session']}"}
    url = f"{server}/api/sheets/{mine['id']}/pdf"
    texts = []
    for solved in (False, True):
        res = httpx.get(url, params={"solved": solved}, headers=cookie, timeout=60)
        assert res.status_code == 200
        pages = PdfReader(io.BytesIO(res.content)).pages
        texts.append(" ".join(page.extract_text() for page in pages))
    assert "Hund" not in texts[0]
    assert "Hund" in texts[1]
