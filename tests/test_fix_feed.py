"""Two fixes in the Lernwörter: the line numbers of a linked text in columns count the rows (#422),
and "Eigener Text" keeps the gaps of a Lückenwörter block (#427).

The docstrings name the lines of the checklist that each test proves.
"""

import re

import pytest
from playwright.sync_api import expect
from test_feed import CHOICE, WORDS
from test_feed_print import hidden_letters, sheet_id
from test_gaps import panel, step
from test_painter import held
from test_words import undo
from ui import RECT, TEXT, apart, at, box, pick, user

from blattwerk import pdf

LISTED = {**TEXT, "list": True}
SIX = WORDS
UNSPLIT = re.compile(r"\bunsplit\b")


@pytest.fixture
def editor(editor):
    """The editor with its panel open, where the tabs Format and Lernwörter are."""

    def start(*blocks, **more):
        return editor(*blocks, theme="", **more)

    return start


def numbers(scope):
    """The numbers beside a text, as they read, once they are drawn for its lines."""
    expect(scope.locator(".numbers")).not_to_have_class(UNSPLIT)
    return scope.locator(".ln")


def paper(browser, server, mine, solved=False):
    """The print page of a sheet, with the answer key when `solved`. The caller closes it."""
    page = browser.new_page(extra_http_headers={"X-Render-Token": pdf.new_token(mine)})
    page.goto(f"{server}/druck/{mine}{'?loesungen' if solved else ''}")
    page.wait_for_selector("body.ready", state="attached")
    return page


@pytest.fixture
def columns(editor):
    """Six words of a linked text in three columns, with a number for every line."""
    client = user()
    page = editor(
        box("a", "text", {**LISTED, "listCols": 3, "lines": 1}, w=180, h=40),
        client=client,
        words=SIX,
    )
    return page


def test_line_numbers_in_columns_count_the_rows(columns):
    """#422 Zeilennummern on a linked text in columns count the rows: six words in three columns
    show 1 and 2, no two numbers at one spot, in the editor."""
    found = numbers(at(columns, "a"))
    expect(found).to_have_count(2)
    assert [el.text_content() for el in found.all()] == ["1", "2"]
    first, second = (float(found.nth(i).get_attribute("y")) for i in (0, 1))
    assert abs(second - first) > 2


@pytest.mark.parametrize("solved", [False, True], ids=["pupils", "key"])
def test_line_numbers_in_columns_print_as_rows(editor, browser, server, solved):
    """#422 Zeilennummern on a linked text in columns count the rows: six words in three columns
    show 1 and 2, no two numbers at one spot, in the PDF and the answer key."""
    client = user()
    page = editor(
        box("a", "text", {**LISTED, "listCols": 3, "lines": 1}, w=180, h=40),
        client=client,
        words=SIX,
    )
    scope = paper(browser, server, sheet_id(page), solved)
    found = scope.locator(".ln")
    expect(found).to_have_count(2)
    assert [el.text_content() for el in found.all()] == ["1", "2"]
    first, second = (float(found.nth(i).get_attribute("y")) for i in (0, 1))
    assert abs(second - first) > 2
    scope.context.close()


def test_every_fifth_line_on_two_rows_shows_no_number(editor):
    """#422 Jede 5. Zeile on two rows shows no number."""
    page = editor(
        box("a", "text", {**LISTED, "listCols": 3, "lines": 5}, w=180, h=40),
        words=SIX,
    )
    assert numbers(at(page, "a")).count() == 0


def test_one_column_still_numbers_each_word(editor):
    """Implied 5: a linked text in one column still numbers each word."""
    page = editor(box("a", "text", {**LISTED, "lines": 1}, w=180, h=60), words=SIX)
    found = numbers(at(page, "a"))
    assert [el.text_content() for el in found.all()] == ["1", "2", "3", "4", "5", "6"]


@pytest.mark.parametrize(
    "kind, props",
    [
        pytest.param("text", TEXT, id="text"),
        pytest.param("shape", {**RECT, **TEXT}, id="shape"),
    ],
)
@pytest.mark.parametrize("mode", ["one", "second"])
def test_eigener_text_keeps_the_gaps(editor, kind, props, mode):
    """#427 Eigener Text on a Lückenwörter block keeps the words with their gaps at the same
    letters, on a text and on a shape. The gaps are plain Lücke gaps from then on; the button
    Lückenwörter goes with the link."""
    client = user()
    linked = {**props, "list": True, "holes": mode, "holeSeed": 7}
    page = editor(box("a", kind, linked), client=client, words=WORDS)
    pick(page, "a")
    before = hidden_letters(at(page, "a").locator(".rich p"))
    assert any(before)
    step(page, lambda: page.get_by_label(CHOICE).select_option(label="Eigener Text"))
    assert hidden_letters(at(page, "a").locator(".rich p")) == before
    stored = held(page, client)["a"]
    assert "list" not in stored
    assert "holes" not in stored
    assert "holeSeed" not in stored
    assert stored["text"] == "\n".join(WORDS)
    gaps = [[run for run in para["runs"] if run.get("gap")] for para in stored["rich"]]
    assert all(len(runs) >= 1 for runs in gaps)
    expect(panel(page, "Lückenwörter")).to_have_count(0)


def test_undo_links_the_block_again(editor):
    """Implied 3: Rückgängig links the block again with its Lückenwörter, in one step."""
    client = user()
    page = editor(
        box("a", "text", {**LISTED, "holes": "one", "holeSeed": 7}),
        client=client,
        words=WORDS,
    )
    pick(page, "a")
    step(page, lambda: page.get_by_label(CHOICE).select_option(label="Eigener Text"))
    step(page, lambda: undo(page))
    back = held(page, client)["a"]
    assert back["list"] is True
    assert back["holes"] == "one"
    assert back["holeSeed"] == 7
    assert "rich" not in back


def test_several_blocks_each_keep_their_gaps(editor):
    """Implied 3: several picked blocks each keep their gaps."""
    client = user()
    page = editor(
        *apart(
            box("a", "text", {**LISTED, "holes": "one", "holeSeed": 7}),
            box("b", "text", {**LISTED, "holes": "one", "holeSeed": 3}, z=2),
        ),
        client=client,
        words=WORDS,
    )
    pick(page, "a", "b")
    before = {name: hidden_letters(at(page, name).locator(".rich p")) for name in ("a", "b")}
    assert before["a"] != before["b"]
    step(page, lambda: page.get_by_label(CHOICE).select_option(label="Eigener Text"))
    for name in ("a", "b"):
        assert hidden_letters(at(page, name).locator(".rich p")) == before[name]


def test_a_block_without_gaps_is_cut_loose_plain(editor):
    """Implied 4: a linked block without Lückenwörter is cut loose as plain words, as before."""
    client = user()
    page = editor(box("a", "text", LISTED), client=client, words=WORDS)
    pick(page, "a")
    step(page, lambda: page.get_by_label(CHOICE).select_option(label="Eigener Text"))
    stored = held(page, client)["a"]
    assert stored["text"] == "\n".join(WORDS)
    assert "rich" not in stored
