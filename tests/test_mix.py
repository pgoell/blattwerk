"""Schüttelwörter, editing side: the switch, its settings, Neu schütteln, undo and redo, several
blocks, the keys, copies, the brush, and a stored mix that is no number.

The tests read what is stored and what the page shows: each scrambled word as the page draws it,
beside the word as typed (`data-mix`). They never work out the order themselves.
"""

import pytest
from playwright.sync_api import expect
from test_gaps import panel, step
from test_lock import FRAMES, fest
from test_painter import held, paint
from ui import RECT, TABLE, TEXT, at, box, pick, user

SCHUTTEL = {**TEXT, "text": "Hund Katze Vogel Schule"}
MIX_PROPS = ("mix", "mixFirst", "mixCaps", "mixLine")
FULL = {"mix": 7, "mixFirst": True, "mixCaps": True}


def mixed(page, name):
    """The scrambled words of a block, as the page draws them, in reading order."""
    return at(page, name).locator(".mix .mixed")


def typed(page, name):
    """The words of a block as typed, in reading order: each scrambled word's `data-mix`."""
    return at(page, name).locator(".mix").evaluate_all("els => els.map((el) => el.dataset.mix)")


@pytest.mark.parametrize(
    "kind, props",
    [
        pytest.param("text", TEXT, id="text"),
        pytest.param("shape", {**RECT, "text": "Hallo"}, id="shape"),
    ],
)
def test_the_switch_stores_a_seed_and_off_removes_it(editor, kind, props):
    client = user()
    page = editor(box("a", kind, props), client=client)
    pick(page, "a")
    switch = panel(page, "Schüttelwörter")
    expect(switch).to_have_attribute("aria-pressed", "false")
    switch.click()
    expect(switch).to_have_attribute("aria-pressed", "true")
    seed = held(page, client)["a"]["mix"]
    assert type(seed) is int and 1 <= seed <= 2147483647
    # "Hallo" has five letters: every one of its words shows in another order.
    shown = mixed(page, "a").all_text_contents()
    for source, now in zip(typed(page, "a"), shown, strict=True):
        if sum(c.isalpha() for c in source) >= 3:
            assert now != source
    switch.click()
    expect(switch).to_have_attribute("aria-pressed", "false")
    assert "mix" not in held(page, client)["a"]


def test_first_letter_and_capitals_are_stored_and_removed_by_a_second_press(editor):
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    pick(page, "a")
    panel(page, "Schüttelwörter").click()
    first = panel(page, "Erster Buchstabe bleibt")
    expect(first).to_have_attribute("aria-pressed", "false")
    first.click()
    expect(first).to_have_attribute("aria-pressed", "true")
    assert held(page, client)["a"]["mixFirst"] is True
    first.click()
    expect(first).to_have_attribute("aria-pressed", "false")
    assert "mixFirst" not in held(page, client)["a"]
    caps = panel(page, "Großbuchstaben")
    caps.click()
    expect(caps).to_have_attribute("aria-pressed", "true")
    assert held(page, client)["a"]["mixCaps"] is True
    for now in mixed(page, "a").all_text_contents():
        assert now == now.upper()
    caps.click()
    expect(caps).to_have_attribute("aria-pressed", "false")
    assert "mixCaps" not in held(page, client)["a"]


def test_neu_schutteln_stores_another_seed_and_every_word_changes(editor):
    client = user()
    page = editor(box("a", "text", SCHUTTEL), client=client)
    pick(page, "a")
    panel(page, "Schüttelwörter").click()
    expect(mixed(page, "a")).to_have_count(4)
    before = mixed(page, "a").all_text_contents()
    seed = held(page, client)["a"]["mix"]
    for _ in range(10):
        step(page, lambda: panel(page, "Neu schütteln").click())
        now = held(page, client)["a"]["mix"]
        assert now != seed
        seed = now
        # The wait: each word must show another order than before the press.
        for i, old in enumerate(before):
            expect(mixed(page, "a").nth(i)).not_to_have_text(old)
        before = mixed(page, "a").all_text_contents()


def test_neu_schutteln_with_no_other_order_makes_no_step(editor):
    """A press that moves no word stores nothing and makes no undo step.

    "Hut" and "Tee" keep one order each, so no seed moves them.
    """
    client = user()
    page = editor(
        box("a", "text", {**TEXT, "text": "Hut Tee", "mix": 7, "mixFirst": True}), client=client
    )
    pick(page, "a")
    undo = page.get_by_label("Rückgängig", exact=True)
    expect(undo).to_be_disabled()
    panel(page, "Neu schütteln").click()
    page.evaluate(FRAMES)
    expect(undo).to_be_disabled()
    assert held(page, client)["a"]["mix"] == 7


def test_neu_schutteln_changes_nothing_else(editor):
    client = user()
    page = editor(
        box("a", "text", {**SCHUTTEL, **FULL, "mixLine": "under"}),
        client=client,
    )
    pick(page, "a")
    expect(panel(page, "Neu schütteln")).to_be_visible()
    before = held(page, client)["a"]
    step(page, lambda: panel(page, "Neu schütteln").click())
    now = held(page, client)["a"]
    assert now["mix"] != before["mix"]
    assert {name: value for name, value in now.items() if name != "mix"} == {
        name: value for name, value in before.items() if name != "mix"
    }
    expect(panel(page, "Erster Buchstabe bleibt")).to_have_attribute("aria-pressed", "true")
    expect(panel(page, "Großbuchstaben")).to_have_attribute("aria-pressed", "true")
    expect(panel(page, "Linie darunter")).to_have_attribute("aria-pressed", "true")


def test_neu_schutteln_never_shows_a_word_as_typed_in_capitals(editor):
    """Every word differs from its typed form in capitals, and from its shown form before the press.

    All five words have two or more orders besides the typed one, and a draw takes a seed that moves
    every word when one exists, so each press moves all five. The check is on every word.
    """
    client = user()
    page = editor(
        box("a", "text", {**TEXT, "text": "Esel Otto Anna Uhu Ebene", "mix": 13, "mixCaps": True}),
        client=client,
    )
    pick(page, "a")
    expect(mixed(page, "a")).to_have_count(5)
    before = mixed(page, "a").all_text_contents()
    sources = typed(page, "a")
    for _ in range(15):
        step(page, lambda: panel(page, "Neu schütteln").click())
        for i in range(5):
            expect(mixed(page, "a").nth(i)).not_to_have_text(before[i])
        now = mixed(page, "a").all_text_contents()
        for i, source in enumerate(sources):
            assert now[i] == now[i].upper()
            assert now[i] != source.upper()
        before = now


def test_the_line_is_none_after_or_under(editor):
    client = user()
    page = editor(box("a", "text", {**TEXT, "mix": 7}), client=client)
    pick(page, "a")
    none = panel(page, "Keine Linie")
    after = panel(page, "Linie dahinter")
    under = panel(page, "Linie darunter")
    expect(none).to_have_attribute("aria-pressed", "true")
    assert "mixLine" not in held(page, client)["a"]
    after.click()
    expect(after).to_have_attribute("aria-pressed", "true")
    expect(none).to_have_attribute("aria-pressed", "false")
    assert held(page, client)["a"]["mixLine"] == "after"
    under.click()
    expect(under).to_have_attribute("aria-pressed", "true")
    expect(after).to_have_attribute("aria-pressed", "false")
    assert held(page, client)["a"]["mixLine"] == "under"
    none.click()
    expect(none).to_have_attribute("aria-pressed", "true")
    assert "mixLine" not in held(page, client)["a"]


def test_undo_and_redo_walk_every_mix_control_one_press_at_a_time(editor):
    client = user()
    page = editor(box("a", "text", SCHUTTEL), client=client)
    pick(page, "a")
    states = [held(page, client)["a"]]
    actions = [
        lambda: panel(page, "Schüttelwörter").click(),
        lambda: panel(page, "Erster Buchstabe bleibt").click(),
        lambda: panel(page, "Großbuchstaben").click(),
        lambda: panel(page, "Linie dahinter").click(),
        lambda: panel(page, "Linie darunter").click(),
        lambda: panel(page, "Neu schütteln").click(),
        lambda: panel(page, "Neu schütteln").click(),
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


def test_several_blocks_get_one_step_and_one_undo(editor):
    client = user()
    page = editor(
        box("a", "text", {**TEXT, "mix": 5}),
        box("b", "text", {**TEXT, "text": "Maus"}, z=2),
        client=client,
    )
    pick(page, "a", "b")
    switch = panel(page, "Schüttelwörter")
    expect(switch).to_have_attribute("aria-pressed", "false")
    step(page, lambda: switch.click())
    expect(switch).to_have_attribute("aria-pressed", "true")
    saved = held(page, client)
    assert saved["a"]["mix"] == saved["b"]["mix"]
    assert 1 <= saved["a"]["mix"] <= 2147483647
    step(page, lambda: page.keyboard.press("Control+z"))
    expect(switch).to_have_attribute("aria-pressed", "false")
    saved = held(page, client)
    assert saved["a"]["mix"] == 5
    assert "mix" not in saved["b"]


def test_neu_schutteln_on_a_text_and_a_shape_is_one_undo_step(editor):
    client = user()
    page = editor(
        box("a", "text", SCHUTTEL),
        box("s", "shape", {**RECT, "text": "Vogel Hund"}, z=2),
        client=client,
    )
    pick(page, "a", "s")
    step(page, lambda: panel(page, "Schüttelwörter").click())
    s0 = {name: held(page, client)[name]["mix"] for name in ("a", "s")}
    step(page, lambda: panel(page, "Neu schütteln").click())
    s1 = {name: held(page, client)[name]["mix"] for name in ("a", "s")}
    assert s1["a"] != s0["a"] and s1["s"] != s0["s"]
    step(page, lambda: page.keyboard.press("Control+z"))
    assert {name: held(page, client)[name]["mix"] for name in ("a", "s")} == s0


def test_the_switch_on_a_group_of_two_texts_mixes_each(editor):
    client = user()
    page = editor(
        box("a", "text", SCHUTTEL, group=["g"]),
        box("b", "text", {**TEXT, "text": "Maus Löwe"}, z=2, group=["g"]),
        client=client,
    )
    at(page, "a").click()
    page.keyboard.press("Control+a")
    expect(page.locator(".block.sel")).to_have_count(2)
    panel(page, "Schüttelwörter").click()
    now = held(page, client)
    assert isinstance(now["a"]["mix"], int) and isinstance(now["b"]["mix"], int)
    expect(mixed(page, "a")).to_have_count(4)
    expect(mixed(page, "b")).to_have_count(2)


def test_tab_reaches_the_mix_controls_and_space_and_enter_press_them(editor):
    """I2: by keyboard alone, the switch; Space presses Schüttelwörter, Enter the first letter."""
    client = user()
    page = editor(box("a", "text", SCHUTTEL), client=client)
    pick(page, "a")
    page.get_by_label("Zeilenabstand").focus()
    for _ in range(7):
        page.keyboard.press("Tab")
    expect(panel(page, "Lösungswörter")).to_be_focused()
    page.keyboard.press("Tab")
    expect(panel(page, "Schüttelwörter")).to_be_focused()
    page.keyboard.press("Space")
    expect(panel(page, "Schüttelwörter")).to_have_attribute("aria-pressed", "true")
    page.keyboard.press("Tab")
    expect(panel(page, "Erster Buchstabe bleibt")).to_be_focused()
    page.keyboard.press("Enter")
    expect(panel(page, "Erster Buchstabe bleibt")).to_have_attribute("aria-pressed", "true")
    assert held(page, client)["a"]["mixFirst"] is True


def test_a_copy_a_duplicate_and_a_reload_keep_the_mix_and_its_order(editor):
    client = user()
    page = editor(
        box("a", "text", {**SCHUTTEL, **FULL, "mixLine": "under"}),
        client=client,
    )
    pick(page, "a")
    before = mixed(page, "a").all_text_contents()
    page.keyboard.press("Control+c")
    page.keyboard.press("Control+v")
    expect(page.locator(".block[data-id]")).to_have_count(2)
    page.keyboard.press("Control+d")
    expect(page.locator(".block[data-id]")).to_have_count(3)
    values = list(held(page, client).values())
    assert values == [values[0]] * 3
    assert {name: values[0][name] for name in MIX_PROPS} == {**FULL, "mixLine": "under"}
    page.reload()
    expect(at(page, "a")).to_be_visible()
    assert mixed(page, "a").all_text_contents() == before
    assert held(page, client)["a"] == values[0]


@pytest.mark.parametrize("kind", ["line", "table", "ruling", "maths", "image", "points"])
def test_a_block_that_holds_no_text_shows_no_switch(editor, kind):
    client = user()
    if kind == "points":
        blocks = [box("fest", kind, {"max": 5})]
    else:
        blocks = [{**b, "locked": False} for b in fest(client, kind)]
    page = editor(*blocks, client=client)
    pick(page, "fest")
    expect(page.locator(".panel h2").first).to_be_visible()
    expect(panel(page, "Schüttelwörter")).to_have_count(0)


def test_the_brush_carries_no_mix(editor):
    """I6: the format painter gives no switch, first letter, capitals or line to another text."""
    client = user()
    page = editor(
        box("a", "text", {**SCHUTTEL, **FULL, "mixLine": "after"}),
        box("b", "text", {**TEXT, "text": "Maus"}, z=2),
        client=client,
    )
    paint(page, "a", "b")
    now = held(page, client)["b"]
    assert not set(MIX_PROPS) & set(now)


def test_a_sheet_without_mix_saves_back_as_it_was(editor):
    """I6: a sheet with no mix saves as it was."""
    client = user()
    old = [
        box("a", "text", TEXT),
        box("c", "shape", {**RECT, "text": "Hund"}, z=2),
        box("t", "table", TABLE, z=3),
    ]
    page = editor(*old, client=client)
    sheet_id = page.url.rsplit("/", 1)[1]
    before = client.get(f"/api/sheets/{sheet_id}").json()["doc"]
    pick(page, "a")
    page.get_by_label("Titel", exact=True).fill("Anders")
    expect(page.locator("header [role=status]")).to_have_text("Gespeichert", timeout=5000)
    after = client.get(f"/api/sheets/{sheet_id}").json()["doc"]
    assert after == before
    for block in before["pages"][0]["blocks"]:
        assert not set(MIX_PROPS) & set(block["props"])


@pytest.mark.parametrize("stored", ["7", None, True], ids=["text-7", "none", "true"])
def test_a_stored_mix_that_is_no_number_shows_the_switch_off(editor, stored):
    page = editor(box("a", "text", {**TEXT, "mix": stored}))
    pick(page, "a")
    expect(panel(page, "Schüttelwörter")).to_have_attribute("aria-pressed", "false")
