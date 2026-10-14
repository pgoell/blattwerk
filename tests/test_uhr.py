"""The Uhr block: its format panel.

The docstrings name what each test proves. The drawing is tested with the model.
"""

import pytest
from playwright.sync_api import expect
from test_gaps import panel, step
from test_words import redo, undo
from ui import box, doc, pick, user

UHR = {
    "numbers": "all",
    "minutes": True,
    "ring": False,
    "task": "read",
    "answer": "box",
    "format": "12",
    "region": "nach",
    "count": 4,
    "cols": 4,
    "step": 15,
    "fill": "random",
    "times": [60, 135, 210, 285],
    "seed": 7,
}


def uhr(name, props):
    """An Uhr block of 180 by 58.5 mm."""
    return box(name, "uhr", props, w=180, h=58.5)


def props_of(stored):
    """The props of the one Uhr of the sheet."""
    [block] = [b for b in stored["pages"][0]["blocks"] if b["type"] == "uhr"]
    return block["props"]


def field(page, label):
    return page.locator(".panel").get_by_label(label, exact=True)


@pytest.mark.parametrize(
    "key, base, before, after, act",
    [
        ("numbers", {}, "all", "quarters", lambda p: field(p, "Zahlen").select_option("quarters")),
        ("minutes", {}, True, False, lambda p: field(p, "Minutenstriche").uncheck()),
        ("ring", {}, False, True, lambda p: field(p, "13 bis 24").check()),
        ("task", {}, "read", "draw", lambda p: field(p, "Aufgabe").select_option("draw")),
        ("answer", {}, "box", "line", lambda p: field(p, "Antwort").select_option("line")),
        ("format", {}, "12", "24", lambda p: field(p, "Schreibweise").select_option("24")),
        (
            "region",
            {"format": "words"},
            "nach",
            "viertel",
            lambda p: field(p, "Form").select_option("viertel"),
        ),
        ("count", {}, 4, 2, lambda p: field(p, "Uhren").fill("2")),
        ("cols", {}, 4, 2, lambda p: field(p, "Spalten").fill("2")),
        ("step", {}, 15, 5, lambda p: field(p, "Schritte").select_option("5")),
        ("fill", {}, "random", "free", lambda p: field(p, "Zeiten").select_option("free")),
    ],
    ids=[
        "zahlen",
        "minutenstriche",
        "ring",
        "aufgabe",
        "antwort",
        "schreibweise",
        "form",
        "uhren",
        "spalten",
        "schritte",
        "zeiten",
    ],
)
def test_each_setting_changes_its_prop_and_undoes_and_redoes(editor, key, base, before, after, act):
    """An Uhr setting stores its prop; Ctrl+Z brings the old value, Ctrl+Y the new."""
    client = user()
    page = editor(uhr("u", {**UHR, **base}), client=client)
    pick(page, "u")
    step(page, lambda: act(page))
    assert props_of(doc(page, client))[key] == after
    undo(page)
    assert props_of(doc(page, client))[key] == before
    redo(page)
    assert props_of(doc(page, client))[key] == after


def test_typing_15_30_into_uhr_1_is_one_undo_step(editor):
    """Typing 15:30 into Uhr 1 is one step and stores 930; one Ctrl+Z brings back 1:00."""
    client = user()
    page = editor(uhr("u", {**UHR, "fill": "free"}), client=client)
    pick(page, "u")
    time = field(page, "Uhr 1")
    step(page, lambda: (time.press("Control+a"), time.press_sequentially("15:30")))
    assert props_of(doc(page, client))["times"][0] == 930
    undo(page)
    assert props_of(doc(page, client))["times"][0] == 60


def test_25_00_is_marked_invalid_and_stores_nothing(editor):
    """25:00 is not a time: the field gets aria-invalid and the stored times stay as they were."""
    client = user()
    page = editor(uhr("u", {**UHR, "fill": "free"}), client=client)
    pick(page, "u")
    time = field(page, "Uhr 1")
    time.press("Control+a")
    time.press_sequentially("25:00")
    expect(time).to_have_attribute("aria-invalid", "true")
    assert props_of(doc(page, client))["times"] == [60, 135, 210, 285]


def test_switching_to_free_keeps_the_times_the_clocks_show(editor):
    """Zeiten to Selbst wählen stores the random times the clocks show, and the fields show them."""
    client = user()
    page = editor(uhr("u", {**UHR, "fill": "random", "times": None}), client=client)
    pick(page, "u")
    step(page, lambda: field(page, "Zeiten").select_option("free"))
    stored = props_of(doc(page, client))
    assert stored["fill"] == "free" and len(stored["times"]) == 4
    for i, t in enumerate(stored["times"]):
        expect(field(page, f"Uhr {i + 1}")).to_have_value(f"{t // 60}:{t % 60:02d}")


def test_neu_wuerfeln_stores_a_new_seed_and_keeps_the_rest(editor):
    """Neu würfeln changes the seed only; the other settings stay."""
    client = user()
    page = editor(uhr("u", dict(UHR)), client=client)
    pick(page, "u")
    step(page, lambda: panel(page, "Neu würfeln").click())
    stored = props_of(doc(page, client))
    assert stored["seed"] != 7
    assert {**stored, "seed": 7} == UHR


def test_form_appears_only_with_in_worten(editor):
    """Form shows only while Schreibweise is In Worten."""
    client = user()
    page = editor(uhr("u", dict(UHR)), client=client)
    pick(page, "u")
    expect(field(page, "Form")).to_have_count(0)
    field(page, "Schreibweise").select_option("words")
    expect(field(page, "Form")).to_have_count(1)
    field(page, "Schreibweise").select_option("24")
    expect(field(page, "Form")).to_have_count(0)


def test_schritte_and_neu_wuerfeln_show_only_for_random(editor):
    """Schritte and Neu würfeln hide once Zeiten is Selbst wählen."""
    client = user()
    page = editor(uhr("u", dict(UHR)), client=client)
    pick(page, "u")
    expect(field(page, "Schritte")).to_have_count(1)
    field(page, "Zeiten").select_option("free")
    expect(field(page, "Schritte")).to_have_count(0)
    expect(panel(page, "Neu würfeln")).to_have_count(0)


def test_antwort_shows_only_for_read(editor):
    """Antwort is the empty answer of Uhrzeit ablesen; it hides for Zeiger einzeichnen."""
    client = user()
    page = editor(uhr("u", dict(UHR)), client=client)
    pick(page, "u")
    expect(field(page, "Antwort")).to_have_count(1)
    field(page, "Aufgabe").select_option("draw")
    expect(field(page, "Antwort")).to_have_count(0)
