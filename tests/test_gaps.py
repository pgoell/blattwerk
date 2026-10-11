"""Lückentext, editing side: gaps of a picked text, their width, the solution words, every n-th
word, undo and redo, and what the field holds of a gap.

The docstrings name the checklist lines. The tests read what is stored and what the field holds,
never how a gap looks.
"""

import pytest
from playwright.sync_api import expect
from test_lock import FRAMES, fest
from test_painter import held, paint
from test_zoom import wheel
from ui import FIELD, RECT, TABLE, TEXT, at, box, caret, pick, user

WORDS = "eins zwei drei vier fünf sechs sieben acht neun zehn"
WORDY = {**TEXT, "text": WORDS}
# Three solution words, so that a Neu mischen moves them: with two, the one order that is not
# the typed one is the only order there is, and a second press moves nothing.
THREE = [
    {
        "runs": [
            {"text": "Hund", "gap": True},
            {"text": " "},
            {"text": "Katze", "gap": True},
            {"text": " "},
            {"text": "Vogel", "gap": True},
        ]
    }
]
TWO = {**TEXT, "text": "Hund Katze Vogel", "rich": THREE}
SHAPE_TWO = {**RECT, "text": "Hund Katze Vogel", "rich": THREE}
GAPPED_TABLE = {**TABLE, "gaps": [[True, True], [True, True]]}
GAPPED = {**TEXT, "rich": [{"runs": [{"text": "Hallo", "gap": True}]}], "gapWidth": 12, "bank": 7}


def panel(page, label):
    return page.locator(".panel").get_by_role("button", name=label, exact=True)


def gapped(rich):
    """The stretches of a stored text that are gaps, in order."""
    return [run["text"] for para in rich for run in para["runs"] if run.get("gap")]


def step(page, action):
    """Does an action that the editor saves, and waits for the save."""
    with page.expect_response(lambda res: res.request.method == "PATCH"):
        action()


def test_lucke_turns_the_picked_words_of_an_open_text_into_a_gap(editor):
    """A1: the picked words of an open text become a gap, shown in the field and saved."""
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    pick(page, "a")
    page.keyboard.press("Enter")
    expect(page.locator(FIELD)).to_be_focused()
    page.keyboard.press("Control+a")
    panel(page, "Lücke").click()
    expect(page.locator(f"{FIELD} .gap")).to_have_count(1)
    assert held(page, client)["a"]["rich"] == [{"runs": [{"text": "Hallo", "gap": True}]}]


def test_lucke_on_a_gap_turns_it_back_into_text(editor):
    """A4: the same button on a gap takes it away; the saved text has no rich form again."""
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    pick(page, "a")
    step(page, lambda: panel(page, "Lücke").click())
    expect(panel(page, "Lücke")).to_have_attribute("aria-pressed", "true")
    step(page, lambda: panel(page, "Lücke").click())
    expect(panel(page, "Lücke")).to_have_attribute("aria-pressed", "false")
    assert "rich" not in held(page, client)["a"]


def test_ctrl_l_makes_no_gap_in_a_block_or_in_an_open_text(editor):
    """A2: Ctrl+L is no shortcut of the gap, neither with the block picked nor in the open text."""
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    pick(page, "a")
    page.keyboard.press("Control+l")
    page.keyboard.press("Enter")
    expect(page.locator(FIELD)).to_be_focused()
    page.keyboard.press("Control+a")
    page.keyboard.press("Control+l")
    expect(page.locator(f"{FIELD} .gap")).to_have_count(0)
    page.keyboard.press("Escape")
    assert "rich" not in held(page, client)["a"]
    assert held(page, client)["a"]["text"] == "Hallo"


def test_lucken_gleich_breit_stores_a_width_that_the_field_changes_and_off_removes_it(editor):
    """A3: the width is stored at 30 mm with no gap drawn; a number changes it; off removes it."""
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    pick(page, "a")
    panel(page, "Lücken gleich breit").click()
    expect(panel(page, "Lücken gleich breit")).to_have_attribute("aria-pressed", "true")
    assert held(page, client)["a"]["gapWidth"] == 30
    width = page.locator(".panel").get_by_label("Breite der Lücken", exact=True)
    width.fill("12")
    width.press("Enter")
    assert held(page, client)["a"]["gapWidth"] == 12
    panel(page, "Lücken gleich breit").click()
    expect(panel(page, "Lücken gleich breit")).to_have_attribute("aria-pressed", "false")
    assert "gapWidth" not in held(page, client)["a"]


def test_losungswörter_stores_a_seed_that_neu_mischen_changes_and_off_removes(editor):
    """A7: the box stores a seed, a new shuffle stores another, and off removes the seed."""
    client = user()
    page = editor(box("a", "text", TWO), client=client)
    pick(page, "a")
    panel(page, "Lösungswörter").click()
    seed = held(page, client)["a"]["bank"]
    assert 1 <= seed <= 2147483647
    panel(page, "Neu mischen").click()
    assert held(page, client)["a"]["bank"] != seed
    panel(page, "Lösungswörter").click()
    assert "bank" not in held(page, client)["a"]


def test_jedes_n_te_wort_gaps_every_fifth_word_and_every_third_when_n_is_three(editor):
    """A8: words 5 and 10 are gaps; with n at 3, words 3, 6 and 9. The text is unchanged."""
    client = user()
    page = editor(box("a", "text", WORDY), client=client)
    pick(page, "a")
    step(page, lambda: panel(page, "Jedes n-te Wort").click())
    assert gapped(held(page, client)["a"]["rich"]) == ["fünf", "zehn"]
    assert held(page, client)["a"]["text"] == WORDS
    page.get_by_label("n", exact=True).fill("3")
    step(page, lambda: panel(page, "Jedes n-te Wort").click())
    assert gapped(held(page, client)["a"]["rich"]) == ["drei", "sechs", "neun"]
    assert held(page, client)["a"]["text"] == WORDS


def test_each_gap_change_is_one_undo_step_and_redo_brings_it_back(editor):
    """A10: each gap change, width, width typed, switch, shuffle and every n-th word is one step."""
    client = user()
    page = editor(box("a", "text", WORDY), client=client)
    pick(page, "a")
    width = page.locator(".panel").get_by_label("Breite der Lücken", exact=True)
    states = [held(page, client)["a"]]
    # Every third word is a gap: three solution words for Neu mischen to move. A gap over the
    # whole text is one solution word, so it comes last.
    page.get_by_label("n", exact=True).fill("3")
    actions = [
        lambda: panel(page, "Lücke").click(),
        lambda: panel(page, "Lücke").click(),
        lambda: panel(page, "Jedes n-te Wort").click(),
        lambda: panel(page, "Lücken gleich breit").click(),
        lambda: (width.fill("12"), width.press("Enter")),
        lambda: panel(page, "Lösungswörter").click(),
        lambda: panel(page, "Neu mischen").click(),
        lambda: panel(page, "Lücke").click(),
    ]
    for act in actions:
        step(page, act)
        states.append(held(page, client)["a"])
    for want in states[-2::-1]:
        step(page, lambda: page.keyboard.press("Control+z"))
        assert held(page, client)["a"] == want
    for want in states[1:]:
        step(page, lambda: page.keyboard.press("Control+y"))
        assert held(page, client)["a"] == want


def test_neu_mischen_on_a_text_and_a_table_is_one_undo_step(editor):
    """A1, A2, I1: a press of Neu mischen on a text and a table is one step; two presses, two."""
    client = user()
    page = editor(box("a", "text", TWO), box("t", "table", GAPPED_TABLE, z=2), client=client)
    pick(page, "a", "t")
    step(page, lambda: panel(page, "Lösungswörter").click())
    s0 = {name: held(page, client)[name]["bank"] for name in ("a", "t")}
    step(page, lambda: panel(page, "Neu mischen").click())
    s1 = {name: held(page, client)[name]["bank"] for name in ("a", "t")}
    assert s1["a"] != s0["a"] and s1["t"] != s0["t"]
    step(page, lambda: panel(page, "Neu mischen").click())
    s2 = {name: held(page, client)[name]["bank"] for name in ("a", "t")}
    assert s2["a"] != s1["a"] and s2["t"] != s1["t"]
    step(page, lambda: page.keyboard.press("Control+z"))
    assert {name: held(page, client)[name]["bank"] for name in ("a", "t")} == s1
    step(page, lambda: page.keyboard.press("Control+z"))
    assert {name: held(page, client)[name]["bank"] for name in ("a", "t")} == s0
    step(page, lambda: page.keyboard.press("Control+y"))
    assert {name: held(page, client)[name]["bank"] for name in ("a", "t")} == s1


def test_neu_mischen_on_a_shape_and_a_table_is_one_undo_step(editor):
    """I2: a press of Neu mischen on a shape with words and a table is one step, one undo."""
    client = user()
    page = editor(
        box("a", "shape", SHAPE_TWO),
        box("t", "table", GAPPED_TABLE, z=2),
        client=client,
    )
    pick(page, "a", "t")
    step(page, lambda: panel(page, "Lösungswörter").click())
    s0 = {name: held(page, client)[name]["bank"] for name in ("a", "t")}
    step(page, lambda: panel(page, "Neu mischen").click())
    assert {name: held(page, client)[name]["bank"] for name in ("a", "t")} != s0
    step(page, lambda: page.keyboard.press("Control+z"))
    assert {name: held(page, client)[name]["bank"] for name in ("a", "t")} == s0


def test_neu_mischen_draws_a_seed_no_selected_block_had(editor):
    """A3: the new seed differs from the old seed of every selected block, not just the first."""
    client = user()
    page = editor(
        box("a", "text", {**TWO, "bank": 5}),
        box("t", "table", {**GAPPED_TABLE, "bank": 7}, z=2),
        client=client,
    )
    pick(page, "a", "t")
    # The first draw gives the table's old seed 7, the next one 9; a draw of n - 0.5 gives n.
    # Then 9 stays.
    page.evaluate(
        """() => {
            const drawn = [7, 9].map((n) => (n - 0.5) / 2147483647);
            Math.random = () => (drawn.length > 1 ? drawn.shift() : drawn[0]);
        }"""
    )
    step(page, lambda: panel(page, "Neu mischen").click())
    now = held(page, client)
    assert now["a"]["bank"] == 9 and now["t"]["bank"] == 9


@pytest.mark.parametrize("kind", ["text", "table"])
def test_lucke_gaps_each_held_block_as_a_whole_when_no_field_is_open(editor, kind):
    """A13 and I2: with no text open, Lücke gaps each block whole: its text, or its cells."""
    client = user()
    blocks = [box("a", "text", WORDY)] if kind == "text" else [box("t", "table", TABLE)]
    page = editor(*blocks, client=client)
    pick(page, "a" if kind == "text" else "t")
    panel(page, "Lücke").click()
    if kind == "text":
        assert gapped(held(page, client)["a"]["rich"]) == [WORDS]
    else:
        assert held(page, client)["t"]["gaps"] == [[True, True], [True, True]]


def test_lucke_gaps_the_words_of_a_shape_with_text(editor):
    """A13: a shape that holds words gets its gap like a text."""
    client = user()
    page = editor(box("a", "shape", {**RECT, "text": "Hund"}), client=client)
    pick(page, "a")
    panel(page, "Lücke").click()
    assert held(page, client)["a"]["rich"] == [{"runs": [{"text": "Hund", "gap": True}]}]


def test_lucke_in_an_open_table_cell_gaps_only_that_cell(editor):
    """A13: with a cell open, Lücke flags that cell alone; gaps has the shape of cells."""
    client = user()
    page = editor(box("t", "table", TABLE), client=client)
    pick(page, "t")
    at(page, "t").locator("[data-cell='2']").dblclick()
    panel(page, "Lücke").click()
    assert held(page, client)["t"]["gaps"] == [[False, False], [True, False]]


def test_lucke_on_a_group_of_two_texts_gaps_each(editor):
    """A13: a group of two texts picked whole: each text gets its gap."""
    client = user()
    page = editor(
        box("a", "text", TEXT, group=["g"]),
        box("b", "text", {**TEXT, "text": "Maus"}, z=2, group=["g"]),
        client=client,
    )
    at(page, "a").click()
    page.keyboard.press("Control+a")
    expect(page.locator(".block.sel")).to_have_count(2)
    panel(page, "Lücke").click()
    now = held(page, client)
    assert gapped(now["a"]["rich"]) == ["Hallo"]
    assert gapped(now["b"]["rich"]) == ["Maus"]


def test_a_caret_in_a_word_gaps_that_word(editor):
    """I1: with a caret in a word and no pick, Lücke gaps that word alone."""
    client = user()
    page = editor(box("a", "text", WORDY), client=client)
    caret(page, "fünf", 2)
    panel(page, "Lücke").click()
    expect(page.locator(f"{FIELD} .gap")).to_have_text("fünf")
    assert gapped(held(page, client)["a"]["rich"]) == ["fünf"]


def test_a_letter_typed_after_a_gap_is_no_part_of_it(editor):
    """I3: a letter typed just after the gap stays out of it."""
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    pick(page, "a")
    page.keyboard.press("Enter")
    expect(page.locator(FIELD)).to_be_focused()
    page.keyboard.press("Control+a")
    panel(page, "Lücke").click()
    page.keyboard.press("End")
    page.keyboard.type("x")
    expect(page.locator(FIELD)).to_have_text("Hallox")
    assert held(page, client)["a"]["rich"] == [
        {"runs": [{"text": "Hallo", "gap": True}, {"text": "x"}]}
    ]


def test_a_letter_typed_right_before_a_gap_is_no_part_of_it(editor):
    """I3: a letter typed just before the gap stays out of it."""
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    pick(page, "a")
    page.keyboard.press("Enter")
    expect(page.locator(FIELD)).to_be_focused()
    page.keyboard.press("Control+a")
    panel(page, "Lücke").click()
    page.keyboard.press("Home")
    page.keyboard.type("x")
    expect(page.locator(FIELD)).to_have_text("xHallo")
    assert held(page, client)["a"]["rich"] == [
        {"runs": [{"text": "x"}, {"text": "Hallo", "gap": True}]}
    ]


def test_the_lucke_button_shows_pressed_in_a_gap_and_keeps_the_field_focused(editor):
    """I4: pressed while the caret stands in a gap; a press on it keeps the field and its typing."""
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    pick(page, "a")
    page.keyboard.press("Enter")
    expect(page.locator(FIELD)).to_be_focused()
    page.keyboard.press("Control+a")
    panel(page, "Lücke").click()
    # At the very start a gap is no mark of the caret; one step in, the caret is inside it.
    page.keyboard.press("Home")
    page.keyboard.press("ArrowRight")
    expect(panel(page, "Lücke")).to_have_attribute("aria-pressed", "true")
    panel(page, "Lücke").click()
    expect(panel(page, "Lücke")).to_have_attribute("aria-pressed", "false")
    expect(page.locator(FIELD)).to_be_focused()
    page.keyboard.type("x")
    expect(page.locator(FIELD)).to_have_text("Hxallo")


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
    page.keyboard.press("Tab")
    page.keyboard.press("Tab")
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


def test_a_shape_with_no_words_takes_no_gap_and_no_step(editor):
    """A13: a shape with no text takes no gap and no every n-th word: its props stay, no step."""
    client = user()
    page = editor(box("s", "shape", RECT), client=client)
    pick(page, "s")
    before = held(page, client)["s"]
    step_free = page.get_by_label("Rückgängig", exact=True)
    expect(step_free).to_be_disabled()
    page.evaluate(FRAMES)
    expect(step_free).to_be_disabled()
    panel(page, "Lücke").click()
    page.evaluate(FRAMES)
    expect(step_free).to_be_disabled()
    panel(page, "Jedes n-te Wort").click()
    page.evaluate(FRAMES)
    expect(step_free).to_be_disabled()
    assert held(page, client)["s"] == before


def test_neu_mischen_never_leaves_the_solution_words_as_they_stood(editor):
    """I3: every press of Neu mischen shows the solution words in another order than before."""
    client = user()
    gapped_words = {
        **TEXT,
        "text": "Hund Katze Vogel",
        "rich": [
            {
                "runs": [
                    {"text": "Hund", "gap": True},
                    {"text": " "},
                    {"text": "Katze", "gap": True},
                    {"text": " "},
                    {"text": "Vogel", "gap": True},
                ]
            }
        ],
        "bank": 7,
    }
    page = editor(box("a", "text", gapped_words), client=client)
    pick(page, "a")
    expect(page.locator(".bank span")).to_have_count(3)
    for _ in range(15):
        before = page.locator(".bank span").all_text_contents()
        step(page, lambda: panel(page, "Neu mischen").click())
        expect(page.locator(".bank span")).not_to_have_text(before)


def test_neu_mischen_with_one_solution_word_makes_no_step(editor):
    """A press of Neu mischen that moves no word stores nothing and makes no undo step."""
    client = user()
    hund = {"runs": [{"text": "Hund", "gap": True}]}
    page = editor(
        box("a", "text", {**TEXT, "text": "Hund", "rich": [hund], "bank": 7}), client=client
    )
    pick(page, "a")
    undo = page.get_by_label("Rückgängig", exact=True)
    expect(undo).to_be_disabled()
    panel(page, "Neu mischen").click()
    page.evaluate(FRAMES)
    expect(undo).to_be_disabled()
    assert held(page, client)["a"]["bank"] == 7


def test_lucken_gleich_breit_takes_the_same_width_at_any_zoom(editor):
    """A3: the width measured at the default zoom is the width measured zoomed in."""
    client = user()
    page = editor(
        box("a", "text", {**TEXT, "rich": [{"runs": [{"text": "Hallo", "gap": True}]}]}),
        client=client,
    )
    pick(page, "a")
    expect(page.locator(".block.sel .gap")).to_have_count(1)
    panel(page, "Lücken gleich breit").click()
    first = held(page, client)["a"]["gapWidth"]
    step(page, lambda: page.keyboard.press("Control+z"))
    wheel(page, -100)
    wheel(page, -100)
    panel(page, "Lücken gleich breit").click()
    assert held(page, client)["a"]["gapWidth"] == first


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
