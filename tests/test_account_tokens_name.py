"""The key's name on Konto: the label, what the field refuses, and the form on a phone.

The account fixture and the helpers live in test_account_tokens.py."""

# The fixture is imported, and each test names it as an argument.
# ruff: noqa: F811

import re

import pytest
from playwright.sync_api import expect
from test_account_tokens import (
    HINT,
    LABEL,
    account,  # noqa: F401
    make,
)
from ui import user


def test_a_blank_name_says_so_beside_the_field(account):
    page = account(user())
    field = page.get_by_label("Name des Schlüssels")
    field.fill("   ")
    page.keyboard.press("Enter")
    expect(field).to_have_accessible_description(re.compile("Gib dem Schlüssel einen Namen\\."))
    expect(page.get_by_test_id("new-token")).to_have_count(0)
    field.fill("x")
    expect(field).to_have_accessible_description(HINT)


def test_a_name_already_in_the_list_says_so_beside_the_field(account):
    page = account(user())
    make(page, "Laptop")
    field = page.get_by_label("Name des Schlüssels")
    field.fill(" laptop ")
    page.keyboard.press("Enter")
    taken = "Diesen Namen hat schon ein Schlüssel. Gib jedem Gerät einen eigenen Namen."
    expect(field).to_have_accessible_description(re.compile(re.escape(taken)))
    expect(page.get_by_role("listitem")).to_have_count(1)


def test_a_name_of_81_letters_stays_whole_and_says_so(account):
    page = account(user())
    field = page.get_by_label("Name des Schlüssels")
    field.fill("x" * 81)
    page.keyboard.press("Enter")
    expect(field).to_have_accessible_description(
        f"{HINT} Der Name ist zu lang: höchstens 80 Zeichen."
    )
    expect(field).to_have_value("x" * 81)


def test_the_key_name_has_a_visible_label_tied_to_the_field(account):
    page = account(user())
    field = page.get_by_role("textbox", name=LABEL)
    expect(field).to_be_visible()
    label_for = page.locator("label", has_text=LABEL).get_attribute("for")
    assert label_for
    expect(field).to_have_attribute("id", label_for)


def test_the_key_name_field_has_no_placeholder(account):
    page = account(user())
    expect(page.get_by_role("textbox", name=LABEL)).to_be_visible()
    assert page.get_by_role("textbox", name=LABEL).get_attribute("placeholder") is None


@pytest.mark.parametrize("dark", [False, True])
def test_the_key_name_field_looks_like_the_other_app_fields(account, dark):
    page = account(user())
    page.emulate_media(color_scheme="dark" if dark else "light")
    field = page.get_by_role("textbox", name=LABEL)
    # A plain text field, as the stylesheet styles every other one, is the reference.
    look = """e => {
        const pick = (s) => ({
            radius: s.borderTopLeftRadius, width: s.borderTopWidth,
            top: s.borderTopColor, right: s.borderRightColor,
            bottom: s.borderBottomColor, left: s.borderLeftColor,
        });
        const plain = document.createElement("input");
        plain.type = "text";
        e.after(plain);
        const reference = pick(getComputedStyle(plain));
        plain.remove();
        return { field: pick(getComputedStyle(e)), reference };
    }"""
    looks = field.evaluate(look)
    assert looks["field"] == looks["reference"]
    assert looks["field"]["width"] == "1px"
    assert looks["field"]["top"] == looks["field"]["left"]


def test_the_hint_for_the_name_sits_by_the_field_and_not_in_the_stop_paragraph(account):
    page = account(user())
    field = page.get_by_role("textbox", name=LABEL)
    expect(page.get_by_text(HINT, exact=True)).to_be_visible()
    expect(field).to_have_attribute("aria-describedby", "name-hint name-note")
    expect(page.locator("p.hint", has_text="Willst du aufhören")).not_to_contain_text("Gerät")


def test_the_key_form_fits_a_375_px_phone(account):
    page = account(user())
    page.set_viewport_size({"width": 375, "height": 800})
    field = page.get_by_role("textbox", name=LABEL)
    expect(field).to_be_visible()
    button = page.get_by_role("button", name="Schlüssel erstellen")
    expect(button).to_be_visible()
    scroll = "() => document.documentElement.scrollWidth <= document.documentElement.clientWidth"
    assert page.evaluate(scroll), "the page scrolls sideways at 375 px"
    for part in (field, button):
        box = part.bounding_box()
        assert box["x"] >= 0 and box["x"] + box["width"] <= 375
