"""Which Halbschriftlich tasks the Zahlenraum, the digits and the Übergänge allow.

The helpers live in test_halbschriftlich.py."""

# The fixture is imported, and each test names it as an argument.
# ruff: noqa: F811

import pytest
from playwright.sync_api import expect
from test_feed_print import sheet_id
from test_halbschriftlich import (
    NO_TASK,
    crosses,
    editor,  # noqa: F401
    field,
    hal,
    values,
)
from test_suchsel_print import key_print
from ui import at, pick


def test_the_zahlenraum_and_the_digits_of_the_second_number_keep_the_rule(editor, browser, server):
    """Zahlenraum (#828): with bis 100 and zweistellig every second number has 2 digits (10 to 99) and every first number
    and result is at most 100. "dreistellig" shows only with bis 1000; a stored 3 with bis 100 reads "zweistellig"."""
    page = editor(hal(props={"max": 100, "digits": 2}))
    pick(page, "k")
    paper = key_print(browser, server, sheet_id(page))
    for task in range(6):
        v = values(paper.locator(".halbschriftlich"), task, 0)
        assert 10 <= v[1] <= 99 and v[0] <= 100 and v[2] <= 100, v
    paper.context.close()
    field(page, "Zahlenraum").select_option(label="bis 100")
    options = field(page, "Stellen der zweiten Zahl").locator("option")
    expect(options).to_have_text(["einstellig", "zweistellig"])
    other = editor(hal(props={"max": 100, "digits": 3}))
    pick(other, "k")
    expect(
        other.locator(".panel")
        .get_by_label("Stellen der zweiten Zahl", exact=True)
        .locator("option:checked")
    ).to_have_text("zweistellig")


def test_the_digits_select_offers_dreistellig_only_with_bis_1000(editor):
    """Zahlenraum (#828): "dreistellig" is offered with bis 1000 and not with bis 100."""
    page = editor(hal())
    pick(page, "k")
    expect(field(page, "Stellen der zweiten Zahl").locator("option")).to_have_text(
        ["einstellig", "zweistellig", "dreistellig"]
    )
    field(page, "Zahlenraum").select_option(label="bis 100")
    expect(field(page, "Stellen der zweiten Zahl").locator("option")).to_have_text(
        ["einstellig", "zweistellig"]
    )


@pytest.mark.parametrize("op", ["+", "-"])
@pytest.mark.parametrize("rule", ["yes", "no"])
def test_uebergang_bei_den_einern_mit_and_ohne_hold_in_every_drawn_task(
    editor,
    browser,
    server,
    op,
    rule,
):
    """Übergang bei den Einern (#828): "mit Übergang" every drawn task crosses in the Einer step, "ohne Übergang"
    none does; read from the digits of the key."""
    page = editor(hal(props={"op": op, "einer": rule}))
    pick(page, "k")
    paper = key_print(browser, server, sheet_id(page))
    for task in range(6):
        v = values(paper.locator(".halbschriftlich"), task, 0)
        assert crosses(op, v[0], v[1], 0) == (rule == "yes"), v
    paper.context.close()


@pytest.mark.parametrize("op", ["+", "-"])
@pytest.mark.parametrize("rule", ["yes", "no"])
def test_uebergang_bei_den_zehnern_mit_and_ohne_hold_in_every_drawn_task(
    editor,
    browser,
    server,
    op,
    rule,
):
    """Übergang bei den Zehnern (#828): with bis 1000 and three digits, "mit Übergang" every drawn task crosses in the
    Zehner step, "ohne Übergang" none does; read from the digits of the key."""
    page = editor(hal(props={"op": op, "zehner": rule}))
    pick(page, "k")
    paper = key_print(browser, server, sheet_id(page))
    for task in range(6):
        v = values(paper.locator(".halbschriftlich"), task, 0)
        assert crosses(op, v[0], v[1], 1) == (rule == "yes"), v
    paper.context.close()


def test_the_zehner_select_shows_only_with_bis_1000(editor):
    """Übergang bei den Zehnern (#828): the select shows with bis 1000, also with einstellig (395 + 7 crosses a
    hundred), and not with bis 100."""
    page = editor(hal())
    pick(page, "k")
    expect(field(page, "Übergang bei den Zehnern")).to_be_visible()
    field(page, "Stellen der zweiten Zahl").select_option(label="einstellig")
    expect(field(page, "Übergang bei den Zehnern")).to_be_visible()
    field(page, "Zahlenraum").select_option(label="bis 100")
    expect(field(page, "Übergang bei den Zehnern")).to_have_count(0)


def test_settings_with_no_task_give_the_hint_and_every_slot_empty_also_in_the_key(
    editor,
    browser,
    server,
):
    """Settings (#828): Plus, bis 1000, einstellig, Einer "ohne Übergang" and Zehner "mit Übergang" give the hint
    "Mit diesen Einstellungen gibt es keine Aufgabe.", and every slot is empty, on the sheet and in the key."""
    page = editor(hal(props={"digits": 1, "einer": "no", "zehner": "yes"}))
    pick(page, "k")
    expect(page.locator(".panel p.hint[role=status]")).to_have_text(NO_TASK)
    expect(at(page, "k").locator(".halbschriftlich text")).to_have_count(0)
    paper = key_print(browser, server, sheet_id(page))
    expect(paper.locator(".halbschriftlich text")).to_have_count(0)
    paper.context.close()


def test_ohne_uebergang_bei_den_zehnern_never_crosses_a_hundred_also_with_einstellig(
    editor,
    browser,
    server,
):
    """Übergang bei den Zehnern (#828): Plus, bis 1000, einstellig, Zehner "ohne Übergang", 12 tasks: in the key no
    task crosses a hundred, so a // 100 equals r // 100 in every task."""
    page = editor(hal(props={"count": 12, "digits": 1, "zehner": "no"}))
    pick(page, "k")
    paper = key_print(browser, server, sheet_id(page))
    loc = paper.locator(".halbschriftlich")
    for task in range(12):
        v = values(loc, task, 0)
        assert v[0] // 100 == v[2] // 100, v
    paper.context.close()
