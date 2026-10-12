"""The Suchsel: a word search block in the editor, its panel, its grid and its answer key.

The docstrings name the lines of the checklist that each test proves. The letters of a grid are
never pinned, only their properties.
"""

from collections import Counter

import pytest
from playwright.sync_api import expect
from test_fields import enter
from test_gaps import panel, step
from test_words import ready, redo, undo
from ui import TEXT, at, box, doc, expect_picked, pick, tool, user

# A Suchsel on the sheet: the thumbnails of the panel Seiten draw every block too, without its id.
ON_SHEET = ".block[data-id] .suchsel"
MIDDLE = """el => {
    const b = el.getBoundingClientRect();
    return [b.x + b.width / 2, b.y + b.height / 2];
}"""
BOX = "el => { const b = el.getBoundingClientRect(); return [b.x, b.y, b.right, b.bottom]; }"
WORDS = ["Hund", "Katze", "Maus", "Vogel", "Pferd", "Schule"]
SUCHSEL = {
    "words": WORDS,
    "cols": 10,
    "rows": 10,
    "ways": "down",
    "caps": True,
    "umlauts": True,
    "show": "words",
    "seed": 7,
}
LERN = ["Reh", "Fuchs"]
LIST8 = ["Hund", "Katze", "Maus", "Vogel", "Pferd", "Schule", "Esel", "Kuh"]
SHORT = ["EIN", "NEIN", "SEE", "TEE"]
EIGHT = [(dc, dr) for dc in (-1, 0, 1) for dr in (-1, 0, 1) if dc or dr]
WAYS = {
    "across": {(1, 0)},
    "down": {(1, 0), (0, 1)},
    "diag": {(1, 0), (0, 1), (1, 1), (1, -1)},
    "back": set(EIGHT),
}


@pytest.fixture
def editor(editor):
    """The editor with its panel open, where the Suchsel's settings are."""

    def start(*blocks, **more):
        return editor(*blocks, theme="", **more)

    return start


def sq(name, props, z=1):
    """A Suchsel block of 120 by 140 mm, which the grid fits with its word list."""
    return box(name, "suchsel", props, z=z, w=120, h=140)


def grid(locator):
    """The letters of a Suchsel, row by row: each row a string of its squares' letters."""
    squares = locator.locator("text[data-at]").evaluate_all(
        "els => els.map((el) => [el.dataset.at, el.textContent])"
    )
    rows = {}
    for where, letter in squares:
        col, row = map(int, where.split(","))
        rows.setdefault(row, {})[col] = letter
    return ["".join(rows[r][c] for c in sorted(rows[r])) for r in sorted(rows)]


def rings(locator):
    """The hidden words of the answer key: where each starts, its way and its length."""
    return locator.locator("rect.ring.answer").evaluate_all(
        """els => els.map((el) => ({
            word: el.dataset.word, col: +el.dataset.col, row: +el.dataset.row,
            dc: +el.dataset.dc, dr: +el.dataset.dr, n: +el.dataset.n }))"""
    )


def spelt(rows, ring):
    """The letters that a ring's squares spell, from its start along its way."""
    return "".join(
        rows[ring["row"] + i * ring["dr"]][ring["col"] + i * ring["dc"]] for i in range(ring["n"])
    )


def spellings(page, name):
    """The words that the rings of a block spell, sorted."""
    rows = grid(at(page, name))
    return sorted(spelt(rows, ring) for ring in rings(at(page, name)))


def covered(ringed):
    """The squares (col, row) that some ring covers."""
    return {(r["col"] + i * r["dc"], r["row"] + i * r["dr"]) for r in ringed for i in range(r["n"])}


def suchsel_props(stored):
    """The props of the one Suchsel of the sheet."""
    [block] = [b for b in stored["pages"][0]["blocks"] if b["type"] == "suchsel"]
    return block["props"]


def hint(page):
    return page.locator(".panel p.hint[role=status]")


def runs_of(rows, word):
    """Each place the word reads in the grid, in the eight ways, with its squares."""
    cols, height = len(rows[0]), len(rows)
    found = []
    for row in range(height):
        for col in range(cols):
            for dc, dr in EIGHT:
                squares = [(col + i * dc, row + i * dr) for i in range(len(word))]
                if all(
                    0 <= x < cols and 0 <= y < height and rows[y][x] == letter
                    for (x, y), letter in zip(squares, word, strict=True)
                ):
                    found.append((col, row, dc, dr, squares))
    return found


def squares_fit(page, name, cols, rows):
    """The squares are square and three letters centred. Gives the square's side."""
    edge = at(page, name).locator("rect.edge").bounding_box()
    side = edge["width"] / cols
    assert side == pytest.approx(edge["height"] / rows, abs=0.5)
    for col, row in ((0, 0), (cols // 2, rows // 2), (cols - 1, rows - 1)):
        # Measured in the page: WebKit gives Playwright another box for a letter of an SVG.
        x, y = at(page, name).locator(f'text[data-at="{col},{row}"]').evaluate(MIDDLE)
        # The box around a letter is as wide as its glyph is set, which lies a hair off its ink.
        assert x - (edge["x"] + (col + 0.5) * side) == pytest.approx(0, abs=0.05 * side)
        assert abs(y - (edge["y"] + (row + 0.5) * side)) <= 0.2 * side
    return side


def test_the_bar_tool_adds_a_ten_by_ten_word_search(editor):
    """A1: the bar's "Suchsel" adds a block of 10 by 10 squares, each with a letter."""
    client = user()
    page = editor(client=client)
    page.get_by_role("toolbar", name="Einfügen").get_by_label("Suchsel", exact=True).click()
    props = suchsel_props(doc(page, client))
    assert (props["cols"], props["rows"]) == (10, 10)
    expect(page.locator(f"{ON_SHEET} text[data-at]")).to_have_count(100)
    assert all(len(row) == 10 and row.isalpha() for row in grid(page.locator(ON_SHEET)))


def test_the_answer_key_spells_each_word_in_capitals(editor):
    """A1: with "Lösungen zeigen" on, six rings spell the six words in capitals."""
    page = editor(sq("s", SUCHSEL))
    tool(page, "Lösungen zeigen").click()
    expect(at(page, "s").locator("rect.ring")).to_have_count(6)
    assert spellings(page, "s") == sorted(word.upper() for word in WORDS)


def test_the_words_field_takes_one_word_to_a_line(editor):
    """A2: the words typed into the field, one to a line, are the block's words and its list."""
    client = user()
    page = editor(sq("s", {**SUCHSEL, "words": []}), client=client)
    pick(page, "s")
    page.get_by_label("Wörter des Suchsels").fill("Hund\nKatze")
    assert suchsel_props(doc(page, client))["words"] == ["Hund", "Katze"]
    expect(at(page, "s").locator("ul.found li")).to_have_text(["Hund", "Katze"])


def test_lernwoerter_uebernehmen_copies_the_sheets_words(editor):
    """A3: one click copies the sheet's Lernwörter into the field, as a copy and not a link."""
    client = user()
    page = editor(sq("s", {**SUCHSEL, "words": []}), client=client, words=LERN)
    pick(page, "s")
    page.get_by_role("button", name="Lernwörter übernehmen", exact=True).click()
    field = page.get_by_label("Wörter des Suchsels")
    expect(field).to_have_value("Reh\nFuchs")
    assert suchsel_props(doc(page, client))["words"] == LERN
    field.fill("Hund")
    assert doc(page, client)["words"] == LERN


def test_lernwoerter_uebernehmen_is_off_without_lernwoerter(editor):
    """A3: with no Lernwörter in the sheet the button "Lernwörter übernehmen" is off."""
    page = editor(sq("s", SUCHSEL))
    pick(page, "s")
    expect(panel(page, "Lernwörter übernehmen")).to_be_disabled()


@pytest.mark.parametrize(
    "key, label, start, limit",
    [
        ("cols", "Eine Spalte weniger", 7, 6),
        ("cols", "Eine Spalte mehr", 19, 20),
        ("rows", "Eine Zeile weniger", 7, 6),
        ("rows", "Eine Zeile mehr", 19, 20),
    ],
)
def test_the_grid_size_runs_from_six_to_twenty(editor, key, label, start, limit):
    """A4: a press moves the grid by one square; at 6 or 20 the button is off."""
    client = user()
    page = editor(sq("s", {**SUCHSEL, key: start}), client=client)
    pick(page, "s")
    step(page, lambda: panel(page, label).click())
    assert suchsel_props(doc(page, client))[key] == limit
    expect(panel(page, label)).to_be_disabled()
    cols, rows = (limit, 10) if key == "cols" else (10, limit)
    expect(at(page, "s").locator("text[data-at]")).to_have_count(cols * rows)


@pytest.mark.parametrize("ways", list(WAYS))
def test_each_direction_setting_allows_only_its_directions(editor, ways):
    """A5: "across" runs left to right only, each level adds ways, "back" runs backwards."""
    props = {**SUCHSEL, "words": LIST8, "cols": 12, "rows": 12, "ways": ways}
    page = editor(*[sq(f"s{n}", {**props, "seed": n}, z=n) for n in range(1, 7)])
    tool(page, "Lösungen zeigen").click()
    found = [ring for n in range(1, 7) for ring in rings(at(page, f"s{n}"))]
    expect(page.locator("rect.ring")).to_have_count(6 * len(LIST8))
    assert {(r["dc"], r["dr"]) for r in found} <= WAYS[ways]
    if ways == "back":
        assert any(r["dc"] < 0 or r["dr"] < 0 for r in found)


def test_capitals_are_on_at_the_start_and_the_toggle_makes_them_small(editor):
    """A6: the letters are capitals at the start; "Nur Großbuchstaben" off makes them all small."""
    page = editor(sq("s", SUCHSEL))
    pick(page, "s")
    toggle = panel(page, "Nur Großbuchstaben")
    expect(toggle).to_have_attribute("aria-pressed", "true")
    assert not any(c.islower() and c != "ß" for c in "".join(grid(at(page, "s"))))
    toggle.click()
    expect(toggle).to_have_attribute("aria-pressed", "false")
    assert not any(c.isupper() for c in "".join(grid(at(page, "s"))))


def test_umlauts_stay_or_become_two_letters(editor):
    """A7: ä, ö, ü and ß stay with the umlaut setting on, and become AE, OE, UE and SS when off."""
    page = editor(sq("s", {**SUCHSEL, "words": ["Käse", "Straße", "Mühle"]}))
    pick(page, "s")
    tool(page, "Lösungen zeigen").click()
    expect(at(page, "s").locator("rect.ring")).to_have_count(3)
    assert spellings(page, "s") == sorted(["KÄSE", "STRAßE", "MÜHLE"])
    panel(page, "Umlaute und ß behalten").click()
    expect(panel(page, "Umlaute und ß behalten")).to_have_attribute("aria-pressed", "false")
    assert spellings(page, "s") == sorted(["KAESE", "STRASSE", "MUEHLE"])


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_fill_never_spells_a_hidden_word_twice(editor, seed):
    """A8: every run of a word that no ring holds has only ring squares in it, in eight ways."""
    props = {**SUCHSEL, "words": SHORT, "cols": 12, "rows": 12, "ways": "back", "seed": seed}
    page = editor(sq("s", props))
    tool(page, "Lösungen zeigen").click()
    expect(at(page, "s").locator("rect.ring")).to_have_count(len(SHORT))
    rows = grid(at(page, "s"))
    ringed = rings(at(page, "s"))
    for word in SHORT:
        starts = {(r["col"], r["row"], r["dc"], r["dr"]) for r in ringed if spelt(rows, r) == word}
        for col, row, dc, dr, squares in runs_of(rows, word):
            ok = (col, row, dc, dr) in starts or set(squares) <= covered(ringed)
            assert ok, (word, col, row, dc, dr)


def test_fill_letters_follow_german_letter_frequency(editor):
    """A8: E is the commonest fill letter; Q, X and Y are rarer than E, N and I."""
    page = editor(sq("s", {**SUCHSEL, "words": ["Hund"], "cols": 20, "rows": 20}))
    tool(page, "Lösungen zeigen").click()
    expect(at(page, "s").locator("rect.ring")).to_have_count(1)
    rows = grid(at(page, "s"))
    shown = covered(rings(at(page, "s")))
    fill = Counter(
        letter for r, row in enumerate(rows) for c, letter in enumerate(row) if (c, r) not in shown
    )
    assert fill.most_common(1)[0][0] == "E"
    assert max(fill[letter] for letter in "QXY") < min(fill[letter] for letter in "ENI")


def test_a_word_that_does_not_fit_is_named_and_the_rest_are_not(editor):
    """A9: a word that fits nowhere is named in the panel with what to loosen; "Hund" is not."""
    props = {**SUCHSEL, "cols": 6, "rows": 6, "ways": "across", "words": ["Schmetterling", "Hund"]}
    page = editor(sq("s", props))
    pick(page, "s")
    expect(hint(page)).to_contain_text("Passt nicht ins Gitter: Schmetterling")
    expect(hint(page)).to_contain_text("mehr Spalten oder Zeilen")
    expect(hint(page)).not_to_contain_text("Hund")


def test_a_word_too_long_for_any_grid_is_named_with_no_false_advice(editor):
    """A9: a word longer than any grid is named, and no advice says to make the grid bigger."""
    words = ["Donaudampfschifffahrtsgesellschaft", "Hund"]
    props = {**SUCHSEL, "cols": 20, "rows": 20, "ways": "back", "words": words}
    page = editor(sq("s", props))
    pick(page, "s")
    expect(hint(page)).to_contain_text(
        "Passt nicht ins Gitter: Donaudampfschifffahrtsgesellschaft."
    )
    expect(hint(page)).to_contain_text("Dafür ist auch das größte Gitter zu klein.")
    expect(hint(page)).not_to_contain_text("Mehr Platz")


def test_the_switch_shows_the_word_list_or_only_the_count(editor):
    """A10: "Nur Anzahl" shows the count instead of the list, and "Wörterliste" the list again."""
    page = editor(sq("s", SUCHSEL))
    pick(page, "s")
    expect(at(page, "s").locator("ul.found li")).to_have_count(6)
    panel(page, "Nur Anzahl").click()
    expect(panel(page, "Nur Anzahl")).to_have_attribute("aria-pressed", "true")
    expect(at(page, "s").locator("p.found")).to_have_text("Finde 6 Wörter.")
    expect(at(page, "s").locator("ul.found")).to_have_count(0)
    panel(page, "Wörterliste").click()
    expect(at(page, "s").locator("ul.found li")).to_have_count(6)


def test_the_layout_comes_from_a_seed_and_neu_wuerfeln_makes_another(editor):
    """A11: two blocks with one seed show one grid, a reload keeps it, "Neu würfeln" changes it."""
    client = user()
    # The second one small and beside the first: a grid is the same at every size.
    beside = {**sq("b", SUCHSEL, z=2), "x": 140, "y": 50, "w": 60, "h": 75}
    page = editor(sq("a", SUCHSEL), beside, client=client)
    before = grid(at(page, "a"))
    assert grid(at(page, "b")) == before
    page.reload()
    ready(page)
    expect(at(page, "a").locator("text[data-at]")).to_have_count(100)
    assert grid(at(page, "a")) == before
    pick(page, "a")
    step(page, lambda: panel(page, "Neu würfeln").click())
    seeds = {b["id"]: b["props"]["seed"] for b in doc(page, client)["pages"][0]["blocks"]}
    assert seeds["a"] != SUCHSEL["seed"] and seeds["b"] == SUCHSEL["seed"]
    assert grid(at(page, "a")) != before


def test_the_answer_key_rings_each_hidden_word(editor):
    """A12: no ring until "Lösungen zeigen" is on, then one ring per hidden word."""
    page = editor(sq("s", SUCHSEL))
    expect(at(page, "s").locator("rect.ring")).to_have_count(0)
    tool(page, "Lösungen zeigen").click()
    expect(at(page, "s").locator("rect.ring")).to_have_count(6)


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_each_ring_lies_around_its_word(editor, seed):
    """A12: each ring lies over its word, its middle between its first and last square's."""
    props = {**SUCHSEL, "ways": "back", "cols": 12, "rows": 12, "words": LIST8, "seed": seed}
    page = editor(sq("s", props))
    tool(page, "Lösungen zeigen").click()
    expect(at(page, "s").locator("rect.ring")).to_have_count(len(LIST8))
    edge = at(page, "s").locator("rect.edge").bounding_box()
    side = edge["width"] / 12

    def middle(col, row):
        return (edge["x"] + (col + 0.5) * side, edge["y"] + (row + 0.5) * side)

    ringed = rings(at(page, "s"))
    shapes = at(page, "s").locator("rect.ring.answer").all()
    for ring, shape in zip(ringed, shapes, strict=True):
        last = (ring["n"] - 1) * ring["dc"], (ring["n"] - 1) * ring["dr"]
        first = middle(ring["col"], ring["row"])
        end = middle(ring["col"] + last[0], ring["row"] + last[1])
        # The SVG rounds each rect to its own pixels: a few tenths of a pixel, one of them 1.1 px.
        middle_of_ends = ((first[0] + end[0]) / 2, (first[1] + end[1]) / 2)
        assert shape.evaluate(MIDDLE) == pytest.approx(middle_of_ends, abs=0.05 * side)
        left, top, right, bottom = shape.evaluate(BOX)
        for x, y in (first, end):
            assert left - 1 <= x <= right + 1 and top - 1 <= y <= bottom + 1
    # A ring straight to the right or down tells nothing of the turn: one must be diagonal or back.
    assert any(r["dc"] * r["dr"] != 0 or min(r["dc"], r["dr"]) < 0 for r in ringed)


def test_the_squares_scale_stay_square_and_centred(editor):
    """A13: the squares fill the room the box leaves and stay square and centred, and grow."""
    page = editor(sq("s", SUCHSEL))
    pick(page, "s")
    small = squares_fit(page, "s", 10, 10)
    enter(page, "Breite", "200")
    enter(page, "Höhe", "240")
    expect(page.locator(".geo").get_by_label("Breite", exact=True)).to_have_value("200")
    assert squares_fit(page, "s", 10, 10) > small


def test_a_wide_low_box_keeps_the_grid_and_its_list_inside(editor):
    """A13: when the height is the limit the squares shrink; grid and list stay in the box."""
    page = editor(sq("s", SUCHSEL))
    pick(page, "s")
    enter(page, "Breite", "180")
    enter(page, "Höhe", "70")
    expect(page.locator(".geo").get_by_label("Höhe", exact=True)).to_have_value("70")
    squares_fit(page, "s", 10, 10)
    block = at(page, "s").bounding_box()
    edge = at(page, "s").locator("rect.edge").bounding_box()
    assert edge["x"] >= block["x"] - 1
    assert edge["x"] + edge["width"] <= block["x"] + block["width"] + 1
    assert edge["y"] >= block["y"] - 1
    assert edge["y"] + edge["height"] <= block["y"] + block["height"] + 1
    found = at(page, "s").locator(".found").bounding_box()
    assert found["y"] >= edge["y"] + edge["height"] - 1
    assert found["y"] + found["height"] <= block["y"] + block["height"] + 1


@pytest.mark.parametrize("what", list(SUCHSEL))
def test_every_setting_undoes_and_redoes(editor, what):
    """A14: a setting changes the block; undo brings the old value, redo the new one."""
    actions = {
        "cols": lambda: panel(page, "Eine Spalte mehr").click(),
        "rows": lambda: panel(page, "Eine Zeile mehr").click(),
        "ways": lambda: page.locator(".panel").get_by_label("Richtungen").select_option("back"),
        "caps": lambda: panel(page, "Nur Großbuchstaben").click(),
        "umlauts": lambda: panel(page, "Umlaute und ß behalten").click(),
        "show": lambda: panel(page, "Nur Anzahl").click(),
        "seed": lambda: panel(page, "Neu würfeln").click(),
        "words": lambda: panel(page, "Lernwörter übernehmen").click(),
    }
    client = user()
    page = editor(sq("s", SUCHSEL), client=client, words=LERN)
    pick(page, "s")
    before = suchsel_props(doc(page, client))[what]
    step(page, actions[what])
    after = suchsel_props(doc(page, client))[what]
    assert after != before
    undo(page)
    assert suchsel_props(doc(page, client))[what] == before
    redo(page)
    assert suchsel_props(doc(page, client))[what] == after


def test_keys_in_the_words_field_edit_the_text_only(editor):
    """I1: Backspace, Delete, arrows and Ctrl+A act in the field; the block stays picked."""
    client = user()
    page = editor(sq("s", {**SUCHSEL, "words": []}), client=client)
    pick(page, "s")
    place = doc(page, client)["pages"][0]["blocks"][0]
    field = page.get_by_label("Wörter des Suchsels")
    field.click()
    page.keyboard.type("Hund")
    for key in ("Backspace", "ArrowLeft", "Delete", "Control+a"):
        page.keyboard.press(key)
    expect(field).to_be_focused()
    expect_picked(page, "s")
    now = doc(page, client)["pages"][0]["blocks"][0]
    assert (now["x"], now["y"]) == (place["x"], place["y"])


def test_ctrl_z_and_ctrl_y_in_the_words_field_undo_and_redo(editor):
    """I2: Ctrl+Z empties the typed words, Ctrl+Y brings them back, as in the Lernwörter."""
    client = user()
    page = editor(sq("s", {**SUCHSEL, "words": []}), client=client)
    pick(page, "s")
    field = page.get_by_label("Wörter des Suchsels")
    field.click()
    page.keyboard.type("Hund")
    expect(field).to_have_value("Hund")
    page.keyboard.press("Control+z")
    expect(field).to_have_value("")
    assert suchsel_props(doc(page, client))["words"] == []
    page.keyboard.press("Control+y")
    expect(field).to_have_value("Hund")
    assert suchsel_props(doc(page, client))["words"] == ["Hund"]


@pytest.mark.parametrize("kind, props", [("suchsel", SUCHSEL), ("text", TEXT)])
def test_the_settings_belong_to_one_block(editor, kind, props):
    """I3: with a Suchsel and another block picked, no words field and no "Neu würfeln"."""
    page = editor(sq("s", SUCHSEL), box("o", kind, props, z=2))
    pick(page, "s", "o")
    expect(page.get_by_label("Wörter des Suchsels")).to_have_count(0)
    expect(panel(page, "Neu würfeln")).to_have_count(0)


@pytest.mark.parametrize("keys", [("Control+c", "Control+v"), ("Control+d",)])
def test_a_copy_shows_the_grid_of_its_source(editor, keys):
    """I4: a pasted or duplicated Suchsel shows the same grid as its source."""
    page = editor(sq("s", SUCHSEL))
    pick(page, "s")
    for key in keys:
        page.keyboard.press(key)
    expect(page.locator(ON_SHEET)).to_have_count(2)
    source, copy = page.locator(ON_SHEET).all()
    expect(copy.locator("text[data-at]")).to_have_count(100)
    assert grid(copy) == grid(source)


def test_a_word_that_does_not_fit_is_not_listed_or_counted(editor):
    """I5: a word that does not fit is in neither the list nor the count."""
    props = {**SUCHSEL, "cols": 6, "rows": 6, "ways": "across"}
    page = editor(sq("s", {**props, "words": ["Schmetterling", "Hund", "Maus"]}))
    pick(page, "s")
    expect(at(page, "s").locator("ul.found li")).to_have_text(["Hund", "Maus"])
    panel(page, "Nur Anzahl").click()
    expect(at(page, "s").locator("p.found")).to_have_text("Finde 2 Wörter.")


def test_a_repeat_is_hidden_once_and_a_short_word_is_named(editor):
    """I6: "Hund" twice is one ring, "Eis-Tee 2" hides EISTEE, and "ab" is named as too short."""
    page = editor(sq("s", {**SUCHSEL, "words": ["Hund", "Hund", "Eis-Tee 2", "ab"]}))
    pick(page, "s")
    expect(hint(page)).to_contain_text("Zu kurz (unter 3 Buchstaben): ab.")
    tool(page, "Lösungen zeigen").click()
    expect(at(page, "s").locator("rect.ring")).to_have_count(2)
    assert spellings(page, "s") == ["EISTEE", "HUND"]


def test_neu_wuerfeln_never_gives_back_a_grid_it_had(editor):
    """I7: five presses of "Neu würfeln" each give a grid that no earlier press gave."""
    page = editor(sq("s", SUCHSEL))
    pick(page, "s")
    grids = [grid(at(page, "s"))]
    for _ in range(5):
        step(page, lambda: panel(page, "Neu würfeln").click())
        grids.append(grid(at(page, "s")))
    for i in range(1, len(grids)):
        assert grids[i] not in grids[:i]
