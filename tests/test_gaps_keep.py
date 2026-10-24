"""What a gap keeps: the hidden word, a copy, a sheet that had none, and the brush.

The gap helpers live in test_gaps.py."""

import pytest
from playwright.sync_api import expect
from test_gaps import (
    GAPPED,
    WORDS,
    WORDY,
    gapped,
    panel,
    step,
)
from test_lock import fest
from test_painter import held, paint
from ui import (
    FIELD,
    RECT,
    TABLE,
    TEXT,
    at,
    box,
    caret,
    pick,
    user,
)


def test_no_hidden_word_is_lost_when_a_gap_is_made_removed_or_typed_at(editor):
    """A12: after each gap change, and typing next to or in a gap, every word is still held."""
    client = user()
    page = editor(box("a", "text", WORDY), client=client)
    caret(page, "fünf", 2)
    panel(page, "Lücke").click()
    assert gapped(held(page, client)["a"]["rich"]) == ["fünf"]
    assert held(page, client)["a"]["text"] == WORDS
    panel(page, "Lücke").click()
    assert "rich" not in held(page, client)["a"]
    panel(page, "Lücke").click()
    page.keyboard.press("ArrowRight")
    page.keyboard.press("ArrowRight")
    page.keyboard.type("x")
    expect(page.locator(FIELD)).to_have_text(WORDS.replace("fünf", "fünfx"))
    now = held(page, client)["a"]
    assert gapped(now["rich"]) == ["fünf"]
    assert now["text"] == WORDS.replace("fünf", "fünfx")
    page.keyboard.press("ArrowLeft")
    page.keyboard.press("ArrowLeft")
    page.keyboard.type("q")
    expect(page.locator(FIELD)).to_have_text(WORDS.replace("fünf", "fünqfx"))
    now = held(page, client)["a"]
    assert gapped(now["rich"]) == ["fünqf"]
    assert now["text"] == WORDS.replace("fünf", "fünqfx")


def test_a_copied_gap_is_a_gap_too_and_undo_redo_and_reload_keep_every_word(editor):
    """A12: a pasted gap is a gap; the first stays whole; undo, redo and reload keep the words."""
    client = user()
    page = editor(box("a", "text", WORDY), client=client)
    caret(page, "fünf", 2)
    panel(page, "Lücke").click()
    before = held(page, client)["a"]
    page.keyboard.press("Home")
    for _ in range(20):
        page.keyboard.press("ArrowRight")
    for _ in range(4):
        page.keyboard.press("Shift+ArrowRight")
    page.keyboard.press("Control+c")
    page.keyboard.press("End")
    page.keyboard.press("Control+v")
    expect(page.locator(FIELD)).to_have_text(WORDS + "fünf")
    now = held(page, client)["a"]
    assert gapped(now["rich"]) == ["fünf", "fünf"]
    assert now["text"] == WORDS + "fünf"
    step(page, lambda: page.keyboard.press("Control+z"))
    assert held(page, client)["a"] == before
    step(page, lambda: page.keyboard.press("Control+y"))
    assert held(page, client)["a"] == now
    page.reload()
    expect(at(page, "a")).to_be_visible()
    assert held(page, client)["a"] == now


@pytest.mark.parametrize("kind", ["line", "image", "symbol", "maths", "ruling", "name", "points"])
def test_a_block_that_holds_no_words_shows_no_gap_controls(editor, kind):
    """A13: a line, picture, symbol, maths, Lineatur, name line and score box have none."""
    client = user()
    if kind in ("name", "points"):
        blocks = [box("fest", kind, {"max": 5} if kind == "points" else {})]
    else:
        blocks = [{**b, "locked": False} for b in fest(client, kind)]
    page = editor(*blocks, client=client)
    pick(page, "fest")
    expect(page.locator(".panel h2").first).to_be_visible()
    # "Lücke" also names a maths exercise's format, so the gap's own neighbours are looked for.
    expect(
        page.locator(".panel").get_by_role("button", name="Jedes n-te Wort", exact=True)
    ).to_have_count(0)
    expect(
        page.locator(".panel").get_by_role("button", name="Lösungswörter", exact=True)
    ).to_have_count(0)


def test_a_sheet_without_gaps_saves_back_as_it_was(editor):
    """A15: a sheet with no gap, of plain and rich text, a shape and a table, saves as it was."""
    client = user()
    rich = {
        **TEXT,
        "text": "Hallo Welt",
        "rich": [{"runs": [{"text": "Hallo ", "bold": True}, {"text": "Welt"}]}],
    }
    old = [
        box("a", "text", TEXT),
        box("b", "text", rich, z=2),
        box("c", "shape", {**RECT, "text": "Hund"}, z=3),
        box("t", "table", TABLE, z=4),
    ]
    page = editor(*old, client=client)
    sheet_id = page.url.rsplit("/", 1)[1]
    before = client.get(f"/api/sheets/{sheet_id}").json()["doc"]
    pick(page, "b")
    page.keyboard.press("Enter")
    expect(page.locator(FIELD)).to_be_focused()
    page.keyboard.press("Escape")
    with page.expect_response(lambda res: res.request.method == "PATCH"):
        page.get_by_label("Titel", exact=True).fill("Anders")
    assert client.get(f"/api/sheets/{sheet_id}").json()["doc"] == before
    for block in before["pages"][0]["blocks"]:
        assert not {"gap", "gaps", "gapWidth", "bank"} & set(block["props"])


def test_tab_reaches_the_gap_controls_and_space_and_enter_press_them(editor):
    """I5: by keyboard alone, the gap controls; Space presses Lücke, Enter presses Lösungswörter."""
    client = user()
    page = editor(box("a", "text", WORDY), client=client)
    pick(page, "a")
    page.get_by_label("Zeilenabstand").focus()
    for _ in range(4):
        page.keyboard.press("Tab")
    expect(panel(page, "Lücke")).to_be_focused()
    page.keyboard.press("Space")
    expect(panel(page, "Lücke")).to_have_attribute("aria-pressed", "true")
    page.keyboard.press("Tab")
    expect(panel(page, "Lücken gleich breit")).to_be_focused()
    page.keyboard.press("Tab")
    expect(page.locator(".panel").get_by_label("n", exact=True)).to_be_focused()
    page.keyboard.press("Tab")
    expect(panel(page, "Jedes n-te Wort")).to_be_focused()
    page.keyboard.press("Tab")
    expect(panel(page, "Lösungswörter")).to_be_focused()
    page.keyboard.press("Enter")
    assert "bank" in held(page, client)["a"]


def test_the_brush_carries_no_gap_gap_width_or_bank(editor):
    """I6: the format painter gives no gap, width or solution words to another text."""
    client = user()
    page = editor(
        box("a", "text", GAPPED), box("b", "text", {**TEXT, "text": "Maus"}, z=2), client=client
    )
    paint(page, "a", "b")
    now = held(page, client)["b"]
    assert not {"rich", "gapWidth", "bank"} & set(now)


def test_a_copy_and_a_duplicate_keep_the_gaps_and_their_settings(editor):
    """I6: copy and paste, and duplicate, keep the gaps, the width and the solution words."""
    client = user()
    page = editor(box("a", "text", GAPPED), client=client)
    pick(page, "a")
    page.keyboard.press("Control+c")
    page.keyboard.press("Control+v")
    expect(page.locator(".block[data-id]")).to_have_count(2)
    page.keyboard.press("Control+d")
    expect(page.locator(".block[data-id]")).to_have_count(3)
    values = list(held(page, client).values())
    assert values == [values[0]] * 3
    assert gapped(values[0]["rich"]) == ["Hallo"]
    assert values[0]["gapWidth"] == 12 and values[0]["bank"] == 7
