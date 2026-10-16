"""A turned group's Breite and Höhe are the size of its own frame, its box at 0 degrees (#666)."""

import pytest
from playwright.sync_api import expect
from test_fields import by_id, enter, field, lock, number
from test_group_scale_turned import PAIR, SHAPES, assert_level_under, pick_group, turned_group
from ui import saved, user


def test_a_turned_group_shows_the_size_of_its_own_frame(editor):
    page = turned_group(editor, user(), *SHAPES)
    assert number(page, "Breite") == pytest.approx(60, abs=0.5)
    assert number(page, "Höhe") == pytest.approx(30, abs=0.5)


def test_breite_typed_on_a_turned_group_is_its_new_own_width(editor):
    client = user()
    page = turned_group(editor, client, *SHAPES)
    enter(page, "Breite", "30")
    expect(field(page, "Breite")).to_have_value("30")
    enter(page, "Drehung", "0")
    expect(field(page, "Drehung")).to_have_value("0")
    assert_level_under(by_id(saved(page, client)))


def test_hoehe_typed_on_a_turned_group_is_its_new_own_height(editor):
    client = user()
    page = turned_group(editor, client, *SHAPES)
    enter(page, "Höhe", "15")
    expect(field(page, "Höhe")).to_have_value("15")
    enter(page, "Drehung", "0")
    expect(field(page, "Drehung")).to_have_value("0")
    rect = by_id(saved(page, client))["a"]
    assert (rect["w"], rect["h"]) == (pytest.approx(60, abs=0.5), pytest.approx(15, abs=0.5))


def test_two_rectangles_turned_as_a_group_show_the_box_around_both(editor):
    page = editor(*PAIR, client=user())
    pick_group(page, "a", "b")
    enter(page, "Drehung", "30")
    expect(field(page, "Drehung")).to_have_value("30")
    assert number(page, "Breite") == pytest.approx(80, abs=0.5)
    assert number(page, "Höhe") == pytest.approx(20, abs=0.5)


def test_with_the_lock_a_turned_group_keeps_its_shape(editor):
    page = turned_group(editor, user(), *SHAPES)
    lock(page).click()
    expect(lock(page)).to_have_attribute("aria-pressed", "true")
    enter(page, "Breite", "30")
    expect(field(page, "Breite")).to_have_value("30")
    assert number(page, "Höhe") == pytest.approx(15, abs=0.5)


def test_a_level_group_still_shows_the_box_around_it(editor):
    page = editor(*PAIR, client=user())
    pick_group(page, "a", "b")
    assert number(page, "Breite") == pytest.approx(80, abs=0.5)
    assert number(page, "Höhe") == pytest.approx(20, abs=0.5)
