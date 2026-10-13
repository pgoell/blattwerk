"""Issue #76: the panel's choices for trace text (Nachspurtext): Aus, Grau, Umriss, Gepunktet.

Checklist ids are in each docstring.
"""

import pytest
from playwright.sync_api import expect
from test_painter import paint
from test_undo_steps import step
from ui import FIELD, RECT, RULING, TABLE, TEXT, at, box, doc, pick, user

CHOICES = ["Aus", "Grau", "Umriss", "Gepunktet"]
KARO = {"kind": "k5", "color": "#222222"}
DOTTED_HINT = "Gepunktet gibt es nur in der Grundschrift (Urff)."


def block(page, client, name):
    return next(b for b in doc(page, client)["pages"][0]["blocks"] if b["id"] == name)


def trace_of(page, client, name):
    return block(page, client, name)["props"].get("trace")


def fade_of(page, client, name):
    return block(page, client, name)["props"].get("fade")


def choose(page, key, which="only"):
    select = page.get_by_label("Nachspurtext", exact=True)
    (select.last if which == "last" else select.first).select_option(key)


def test_a_lineatur_has_four_choices(editor):
    """B1: the Lineatur's select has four choices in order; each stores its trace."""
    client = user()
    page = editor(box("l1", "ruling", RULING), client=client)
    pick(page, "l1")
    select = page.get_by_label("Nachspurtext", exact=True)
    expect(select.locator("option")).to_have_text(CHOICES)
    choose(page, "grey")
    expect(select).to_have_value("grey")
    assert trace_of(page, client, "l1") is True
    choose(page, "off")
    expect(select).to_have_value("off")
    assert trace_of(page, client, "l1") is None


@pytest.mark.parametrize("kind", ["text", "karo"])
def test_dotted_is_off_for_a_font_without_a_cut(editor, kind):
    """B4: Gepunktet is off in Andika and for Karo, with a hint; Urff enables it."""
    client = user()
    if kind == "text":
        page = editor(box("a", "text", TEXT), client=client)
        pick(page, "a")
    else:
        page = editor(box("a", "ruling", KARO), client=client)
        pick(page, "a")
    select = page.get_by_label("Nachspurtext", exact=True)
    expect(select.locator("option", has_text="Gepunktet")).to_be_disabled()
    expect(page.get_by_text(DOTTED_HINT)).to_be_visible()
    if kind == "text":
        page.get_by_label("Schriftart", exact=True).select_option("urff")
        expect(select.locator("option", has_text="Gepunktet")).to_be_enabled()
        expect(page.get_by_text(DOTTED_HINT)).to_have_count(0)
        choose(page, "dotted")
        assert trace_of(page, client, "a") == "dotted"


def test_dotted_without_a_cut_shows_grey(editor):
    """B4: a stored "dotted" in a font without a cut shows Grau."""
    client = user()
    page = editor(box("a", "text", {**TEXT, "trace": "dotted"}), client=client)
    pick(page, "a")
    expect(page.get_by_label("Nachspurtext", exact=True)).to_have_value("grey")


@pytest.mark.parametrize("kind", ["text", "table", "lineatur"])
def test_fading_switch_and_direction(editor, kind):
    """B5: Ausblenden shows only with a look on; the directions store "row" and "rows"."""
    client = user()
    props = {"text": TEXT, "table": TABLE, "lineatur": RULING}[kind]
    page = editor(
        box("a", {"text": "text", "table": "table", "lineatur": "ruling"}[kind], props),
        client=client,
    )
    pick(page, "a")
    expect(page.get_by_role("button", name="Ausblenden")).to_have_count(0)
    choose(page, "outline")
    page.get_by_role("button", name="Ausblenden").click()
    assert fade_of(page, client, "a") == "row"
    expect(page.get_by_role("button", name="In der Zeile")).to_have_attribute(
        "aria-pressed", "true"
    )
    page.get_by_role("button", name="Von Zeile zu Zeile").click()
    assert fade_of(page, client, "a") == "rows"
    page.get_by_role("button", name="Ausblenden").click()
    assert fade_of(page, client, "a") is None


@pytest.mark.parametrize("kind", ["text", "lineatur"])
def test_each_choice_is_one_undo_step(editor, kind):
    """B8: each choice is one undo step; redo walks them forward again."""
    client = user()
    page = editor(
        box("a", "text", TEXT) if kind == "text" else box("a", "ruling", RULING), client=client
    )
    pick(page, "a")
    choose(page, "outline")
    page.get_by_role("button", name="Ausblenden").click()
    page.get_by_role("button", name="Von Zeile zu Zeile").click()
    for _ in range(3):
        step(page, lambda: page.keyboard.press("Control+z"))
    expect(page.get_by_label("Nachspurtext", exact=True)).to_have_value("off")
    for _ in range(3):
        step(page, lambda: page.keyboard.press("Control+y"))
    expect(page.get_by_label("Nachspurtext", exact=True)).to_have_value("outline")
    assert fade_of(page, client, "a") == "rows"
    # Aus is one step too, and its undo brings back the trace and the fading together.
    choose(page, "off")
    assert trace_of(page, client, "a") is None
    step(page, lambda: page.keyboard.press("Control+z"))
    assert trace_of(page, client, "a") == "outline"
    assert fade_of(page, client, "a") == "rows"


@pytest.mark.parametrize(
    "kind",
    ["text", "shape", "table", "lineatur", "karo", "group"],
)
def test_every_block_with_text_has_the_choice(editor, kind):
    """B2: every block with text has the select; Umriss stores "outline" on it, or its member."""
    client = user()
    blocks = {
        "text": [box("a", "text", TEXT)],
        "shape": [box("a", "shape", {**RECT, "text": "Im Kasten"})],
        "table": [box("a", "table", TABLE)],
        "lineatur": [box("a", "ruling", RULING)],
        "karo": [box("a", "ruling", KARO)],
        "group": [
            box("a", "text", TEXT, w=40, group=["g"]),
            box("b", "text", TEXT, z=2, x=60, y=50, w=40, group=["g"]),
        ],
    }[kind]
    page = editor(*blocks, client=client)
    if kind == "group":
        at(page, "a").click()
        expect(page.locator(".block.sel")).to_have_count(2)
    else:
        pick(page, "a")
    expect(page.get_by_label("Nachspurtext", exact=True)).to_be_visible()
    choose(page, "outline")
    assert trace_of(page, client, "a") == "outline"


@pytest.mark.parametrize("which", ["first", "last"])
def test_one_choice_sets_all_picked_blocks(editor, which):
    """I1: one choice sets Umriss on every picked block with text; one Control+z undoes all."""
    client = user()
    page = editor(
        box("a", "text", TEXT),
        box("c", "shape", {**RECT, "text": "Im Kasten"}, z=2),
        box("t", "table", TABLE, z=3),
        box("l1", "ruling", RULING, z=4),
        box("k", "ruling", KARO, z=5),
        client=client,
    )
    names = ["a", "c", "t", "l1", "k"]
    pick(page, *names)
    choose(page, "outline", which)
    for name in names:
        assert trace_of(page, client, name) == "outline"
    step(page, lambda: page.keyboard.press("Control+z"))
    for name in names:
        assert trace_of(page, client, name) is None


def test_a_lineatur_of_lernwoerter_takes_no_look(editor):
    """I1: picked with a text, a Lineatur that shows the Lernwörter keeps what it stores."""
    client = user()
    linked = {**RULING, "kind": "l1", "list": "trace", "trace": True}
    page = editor(
        box("a", "text", TEXT),
        box("r", "ruling", linked, z=2, h=40),
        client=client,
        words=["Hund", "Katze"],
    )
    pick(page, "a", "r")
    choose(page, "outline")
    assert trace_of(page, client, "a") == "outline"
    assert trace_of(page, client, "r") is True


def test_aus_takes_the_fading_along(editor):
    """Aus removes the trace and its fading: no key is left, and a later Grau is not faded."""
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    pick(page, "a")
    choose(page, "outline")
    page.get_by_role("button", name="Ausblenden").click()
    choose(page, "off")
    props = block(page, client, "a")["props"]
    assert "trace" not in props and "fade" not in props
    choose(page, "grey")
    assert trace_of(page, client, "a") is True
    assert "fade" not in block(page, client, "a")["props"]


def test_the_open_text_shows_the_look(editor):
    """I2: a choice in the panel gives the keys back to the open text, which shows the look."""
    client = user()
    page = editor(box("a", "text", TEXT), client=client)
    pick(page, "a")
    page.keyboard.press("Enter")
    choose(page, "outline")
    expect(page.locator(FIELD)).to_be_focused()
    page.keyboard.type("x")
    expect(page.locator(FIELD)).to_have_text("x")
    expect(page.locator(".block.sel .frame")).to_have_attribute(
        "data-trace", "outline"
    )  # needs the drawing


@pytest.mark.parametrize("case", ["text", "lineatur", "no_trace"])
def test_the_brush_carries_the_look(editor, case):
    """I3: the brush carries trace and fade; a block without trace takes none away."""
    client = user()
    if case == "text":
        page = editor(
            box("a", "text", {**TEXT, "trace": "outline", "fade": "rows"}),
            box("b", "text", TEXT, z=2),
            client=client,
        )
        paint(page, "a", "b")
        assert trace_of(page, client, "b") == "outline"
        assert fade_of(page, client, "b") == "rows"
    elif case == "lineatur":
        page = editor(
            box("a", "ruling", {**RULING, "trace": "dotted"}),
            box("b", "ruling", RULING, z=2),
            client=client,
        )
        paint(page, "a", "b")
        assert trace_of(page, client, "b") == "dotted"
    else:
        page = editor(
            box("a", "text", TEXT),
            box("b", "text", {**TEXT, "trace": True}, z=2),
            client=client,
        )
        paint(page, "a", "b")
        assert trace_of(page, client, "b") is None
